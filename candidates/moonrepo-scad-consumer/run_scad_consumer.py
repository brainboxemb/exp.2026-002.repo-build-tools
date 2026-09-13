#!/usr/bin/env python3
"""Qualify moonrepo against a real template.scad-project consumer."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "candidates" / "moonrepo-scad-consumer"
TEMPLATE_REPO = "https://github.com/brainboxemb/template.scad-project.git"
TEMPLATE_SHA = "be344c59d310747a480a1606d81ec7534a5b99c3"
TEMPLATE_TOOL_SHA = "40694891d3239401cb0ba4bfb35a3812d6584ab7"
TOOL_SHA = "0469bc14afe1600484d20441269b06608b8f6179"


def run(argv: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(argv)}\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def patch_text(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected pin {old} not found in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def init_workspace(path: Path) -> None:
    run(["git", "clone", "--recurse-submodules", "--no-tags", TEMPLATE_REPO, str(path)], ROOT)
    run(["git", "checkout", "--detach", TEMPLATE_SHA], path)
    run(["git", "submodule", "update", "--init"], path)

    tool = path / "tools" / "tool.scad-project"
    run(["git", "fetch", "origin", "main"], tool)
    run(["git", "checkout", "--detach", TOOL_SHA], tool)

    patch_text(path / "project.yml", TEMPLATE_TOOL_SHA, TOOL_SHA)
    for workflow in sorted((path / ".github" / "workflows").glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        if TEMPLATE_TOOL_SHA in text:
            workflow.write_text(text.replace(TEMPLATE_TOOL_SHA, TOOL_SHA), encoding="utf-8")

    # Keep the template's functional verification aligned with the exact experimental tool checkout.
    shutil.copy2(tool / "bootstrap" / "consumer-update.sh", path / "update-repo.sh")
    shutil.copy2(tool / "bootstrap" / "consumer-update.ps1", path / "update-repo.ps1")

    shutil.copytree(CANDIDATE / ".moon", path / ".moon", dirs_exist_ok=True)
    shutil.copy2(CANDIDATE / "moon.yml", path / "moon.yml")
    experiment = path / ".experiment"
    experiment.mkdir(exist_ok=True)
    shutil.copy2(CANDIDATE / "scad_build.sh", experiment / "scad_build.sh")
    shutil.copy2(CANDIDATE / "scad_verify.sh", experiment / "scad_verify.sh")
    (experiment / "tool-scad-project.sha").write_text(TOOL_SHA + "\n", encoding="utf-8")


def run_verify(moon: str, path: Path) -> dict:
    result = run([moon, "run", "consumer:scad.verify", "--log", "info"], path)
    return {"stdout": result.stdout, "stderr": result.stderr}


def count(path: Path, task: str) -> int:
    file = path / ".experiment-state" / f"{task}.count"
    return int(file.read_text(encoding="utf-8")) if file.is_file() else 0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(path: Path) -> dict[str, str]:
    required = [
        "bld/png/tube-holder-assembly.png",
        "bld/stl/tube-holder-assembly.stl",
        "bld/publication-info.txt",
        "evidence/scad-build/execution.json",
        "evidence/scad-build/execution.log",
        "evidence/scad-build/domain/last-build.json",
        "evidence/scad-build/domain/last-design-build.json",
        "vrf/out/png/tube-holder-bore-check.png",
        "vrf/out/png/mounting-plate-thickness-check.png",
        "vrf/out/publication-info.txt",
        "evidence/scad-verify/execution.json",
        "evidence/scad-verify/execution.log",
        "evidence/scad-verify/domain/last-verification-build.json",
    ]
    missing = [relative for relative in required if not (path / relative).is_file()]
    if missing:
        raise RuntimeError(f"missing SCAD outputs/evidence: {missing}")
    return {relative: sha256(path / relative) for relative in required}


def outcomes(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("outcome_counts", {})
    return {name: int(raw.get(name, 0)) for name in ("BUILT", "CACHE_RESTORED", "CURRENT", "ERROR")}


def copy_portable_cache(source: Path, destination: Path) -> list[str]:
    copied = []
    for name in ("hashes", "outputs"):
        src = source / ".moon" / "cache" / name
        require(src.is_dir(), f"moon portable cache directory missing: {src}")
        dst = destination / ".moon" / "cache" / name
        shutil.copytree(src, dst, dirs_exist_ok=True)
        copied.append(name)
    return copied


def append_comment(path: Path, marker: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n// {marker}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--moon", default="moon")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    moon_version = run([args.moon, "--version"], ROOT).stdout.strip()

    with tempfile.TemporaryDirectory(prefix="moon-scad-source-") as first_temp:
        first = Path(first_temp)
        init_workspace(first)

        cold = run_verify(args.moon, first)
        require(count(first, "scad-build") == 1, "cold SCAD build did not execute exactly once")
        require(count(first, "scad-verify") == 1, "cold SCAD verify did not execute exactly once")
        cold_snapshot = snapshot(first)
        cold_build = outcomes(first / "evidence/scad-build/domain/last-build.json")
        cold_design = outcomes(first / "evidence/scad-build/domain/last-design-build.json")
        cold_verify = outcomes(first / "evidence/scad-verify/domain/last-verification-build.json")
        require(cold_build["BUILT"] > 0 and cold_build["ERROR"] == 0, "cold normal build telemetry is not healthy")
        require(cold_design["BUILT"] > 0 and cold_design["ERROR"] == 0, "cold design telemetry is not healthy")
        require(cold_verify["BUILT"] > 0 and cold_verify["ERROR"] == 0, "cold verification telemetry is not healthy")

        exact = run_verify(args.moon, first)
        require(count(first, "scad-build") == 1, "exact rerun unexpectedly executed SCAD build")
        require(count(first, "scad-verify") == 1, "exact rerun unexpectedly executed SCAD verify")
        require(snapshot(first) == cold_snapshot, "exact rerun changed cached SCAD outputs/evidence")

        for relative in ("bld", "vrf/out", "evidence"):
            shutil.rmtree(first / relative)
        hydrated = run_verify(args.moon, first)
        require(count(first, "scad-build") == 1, "local hydration unexpectedly executed SCAD build")
        require(count(first, "scad-verify") == 1, "local hydration unexpectedly executed SCAD verify")
        require(snapshot(first) == cold_snapshot, "local hydration did not restore exact SCAD output/evidence")

        with tempfile.TemporaryDirectory(prefix="moon-scad-fresh-") as second_temp:
            second = Path(second_temp)
            init_workspace(second)
            copied_cache = copy_portable_cache(first, second)
            fresh = run_verify(args.moon, second)
            require(count(second, "scad-build") == 0, "fresh hydration executed SCAD build")
            require(count(second, "scad-verify") == 0, "fresh hydration executed SCAD verify")
            require(snapshot(second) == cold_snapshot, "fresh hydration did not restore exact SCAD output/evidence")

        append_comment(first / "vrf/openscad/tube_holder_bore_check.scad", "r1c verification-only mutation")
        changed_verification = run_verify(args.moon, first)
        require(count(first, "scad-build") == 1, "verification-only change unexpectedly executed SCAD build")
        require(count(first, "scad-verify") == 2, "verification-only change did not execute SCAD verify")
        verification_selective = outcomes(first / "evidence/scad-verify/domain/last-verification-build.json")
        require(verification_selective["BUILT"] > 0, "verification-only change rebuilt no verification target")
        require(
            verification_selective["CURRENT"] + verification_selective["CACHE_RESTORED"] > 0,
            "verification-only change showed no fine-grained SCons reuse",
        )

        append_comment(first / "dsg/openscad/components/tube/tube.scad", "r1c product-source mutation")
        changed_source = run_verify(args.moon, first)
        require(count(first, "scad-build") == 2, "SCAD source change did not execute build")
        require(count(first, "scad-verify") == 3, "SCAD source change did not execute downstream verify")
        design_selective = outcomes(first / "evidence/scad-build/domain/last-design-build.json")
        require(design_selective["BUILT"] > 0, "SCAD source change rebuilt no design target")
        require(
            design_selective["CURRENT"] + design_selective["CACHE_RESTORED"] > 0,
            "SCAD source change showed no fine-grained SCons reuse in design targets",
        )

        payload = {
            "candidate": "moonrepo-scad-consumer",
            "moon_version": moon_version,
            "template_repository": "brainboxemb/template.scad-project",
            "template_sha": TEMPLATE_SHA,
            "tool_scad_project_sha": TOOL_SHA,
            "toolchain": "ghcr.io/brainboxemb/scad-toolchain:v0.4.1",
            "portable_cache_directories": copied_cache,
            "checks": {
                "cold_real_scad_build_and_verify_execute": True,
                "scad_decision_telemetry_preserved": True,
                "exact_rerun_skips_build_and_verify": True,
                "deleted_scad_outputs_hydrate_without_commands": True,
                "fresh_workspace_hydrates_outputs_logs_and_telemetry": True,
                "verification_only_change_executes_only_verify": True,
                "verification_scons_selectivity_preserved": True,
                "source_change_executes_build_and_downstream_verify": True,
                "design_scons_selectivity_preserved": True,
            },
            "outcomes": {
                "cold_build": cold_build,
                "cold_design": cold_design,
                "cold_verify": cold_verify,
                "verification_only_change": verification_selective,
                "source_change_design": design_selective,
            },
            "execution_counts": {
                "final": {
                    "scad.build": count(first, "scad-build"),
                    "scad.verify": count(first, "scad-verify"),
                }
            },
            "runs": {
                "cold": cold,
                "exact_rerun": exact,
                "local_hydration": hydrated,
                "fresh_workspace_hydration": fresh,
                "verification_only_change": changed_verification,
                "source_change": changed_source,
            },
            "architecture_notes": [
                "moon provides exact high-level task output hydration",
                "SCons remains authoritative for per-target decisions when a SCAD task executes",
                "cross-revision SCons cache persistence remains a separate concern from moon exact task caching",
                "the proof composes scad.build with functional-verify because the current reusable Verify workflow also rebuilds normal outputs",
            ],
        }

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            evidence_out = args.output.parent / "evidence"
            if evidence_out.exists():
                shutil.rmtree(evidence_out)
            shutil.copytree(first / "evidence", evidence_out)

    print(
        "PASS moon + real SCAD consumer: task hydration, durable logs/telemetry, "
        "verification-only selection, and nested SCons selectivity"
    )


if __name__ == "__main__":
    main()
