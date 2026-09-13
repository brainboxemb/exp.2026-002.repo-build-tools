#!/usr/bin/env python3
"""Qualify moon as a high-level task/output-cache orchestrator."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "candidates" / "moonrepo-orchestration"


def run(argv: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(argv)}\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result


def init_workspace(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CANDIDATE / ".moon", path / ".moon")
    shutil.copy2(CANDIDATE / "moon.yml", path / "moon.yml")
    shutil.copytree(CANDIDATE / "tools", path / "tools")

    (path / "src/product").mkdir(parents=True)
    (path / "release").mkdir(parents=True)
    (path / "src/product/core.txt").write_text("product-source-v1\n", encoding="utf-8")
    (path / "release/metadata.txt").write_text("release-metadata-v1\n", encoding="utf-8")
    (path / "README.md").write_text("fixture workspace\n", encoding="utf-8")
    (path / ".gitignore").write_text(
        ".moon/cache/\nout/\n.executions/\n",
        encoding="utf-8",
    )

    run(["git", "init", "-b", "main"], path)
    run(["git", "config", "user.name", "repo-build-tools-experiment"], path)
    run(["git", "config", "user.email", "experiment@example.invalid"], path)
    run(["git", "add", "."], path)
    run(["git", "commit", "-m", "baseline"], path)


def run_publication(moon: str, path: Path) -> dict:
    result = run([moon, "run", "fixture:publication", "--log", "info"], path)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def count(path: Path, name: str) -> int:
    counter = path / ".executions" / f"{name}.count"
    return int(counter.read_text(encoding="utf-8")) if counter.exists() else 0


def snapshot(path: Path) -> dict:
    required = {
        "product_artifact": path / "out/product/artifact.txt",
        "product_execution_json": path / "out/product/evidence/execution.json",
        "product_execution_log": path / "out/product/evidence/execution.log",
        "publication_package": path / "out/publication/package.txt",
        "publication_execution_json": path / "out/publication/evidence/execution.json",
        "publication_execution_log": path / "out/publication/evidence/execution.log",
    }
    missing = [name for name, file in required.items() if not file.is_file()]
    if missing:
        raise RuntimeError(f"missing output/evidence files: {missing}")
    return {name: file.read_text(encoding="utf-8") for name, file in required.items()}


def copy_portable_cache(source: Path, destination: Path) -> list[str]:
    copied = []
    for name in ("hashes", "outputs"):
        src = source / ".moon" / "cache" / name
        if not src.is_dir():
            raise RuntimeError(f"moon portable cache directory missing: {src}")
        dst = destination / ".moon" / "cache" / name
        shutil.copytree(src, dst, dirs_exist_ok=True)
        copied.append(name)
    return copied


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--moon", default="moon")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    moon_version = run([args.moon, "--version"], ROOT).stdout.strip()

    with tempfile.TemporaryDirectory(prefix="moon-orchestration-source-") as first_temp:
        first = Path(first_temp)
        init_workspace(first)

        cold = run_publication(args.moon, first)
        require(count(first, "product") == 1, "cold product build did not execute exactly once")
        require(count(first, "publication") == 1, "cold publication did not execute exactly once")
        cold_snapshot = snapshot(first)

        exact = run_publication(args.moon, first)
        require(count(first, "product") == 1, "exact rerun unexpectedly executed product build")
        require(count(first, "publication") == 1, "exact rerun unexpectedly executed publication")
        require(snapshot(first) == cold_snapshot, "exact rerun changed cached outputs/evidence")

        shutil.rmtree(first / "out")
        hydrate = run_publication(args.moon, first)
        require(count(first, "product") == 1, "local hydration unexpectedly executed product build")
        require(count(first, "publication") == 1, "local hydration unexpectedly executed publication")
        require(snapshot(first) == cold_snapshot, "local hydration did not restore exact outputs/evidence")

        with tempfile.TemporaryDirectory(prefix="moon-orchestration-fresh-") as second_temp:
            second = Path(second_temp)
            init_workspace(second)
            copied_cache = copy_portable_cache(first, second)

            fresh = run_publication(args.moon, second)
            require(count(second, "product") == 0, "fresh cache hydration executed product build")
            require(count(second, "publication") == 0, "fresh cache hydration executed publication")
            require(snapshot(second) == cold_snapshot, "fresh cache hydration did not restore exact outputs/evidence")

            with (second / "src/product/core.txt").open("a", encoding="utf-8") as handle:
                handle.write("product-source-v2\n")
            run(["git", "add", "src/product/core.txt"], second)
            run(["git", "commit", "-m", "change product source"], second)

            changed_product = run_publication(args.moon, second)
            require(count(second, "product") == 1, "changed product input did not execute product build")
            require(count(second, "publication") == 1, "changed product input did not execute downstream publication")
            changed_snapshot = snapshot(second)
            require(
                changed_snapshot["product_artifact"] != cold_snapshot["product_artifact"],
                "changed product input did not change product artifact",
            )
            require(
                changed_snapshot["publication_package"] != cold_snapshot["publication_package"],
                "changed product input did not change publication package",
            )

            with (second / "release/metadata.txt").open("a", encoding="utf-8") as handle:
                handle.write("release-metadata-v2\n")
            run(["git", "add", "release/metadata.txt"], second)
            run(["git", "commit", "-m", "change release metadata"], second)

            changed_release = run_publication(args.moon, second)
            require(count(second, "product") == 1, "release-only change unexpectedly executed product build")
            require(count(second, "publication") == 2, "release-only change did not execute publication")

            payload = {
                "candidate": "moonrepo-orchestration",
                "moon_version": moon_version,
                "platform": args.platform,
                "portable_cache_directories": copied_cache,
                "checks": {
                    "cold_executes_producer": True,
                    "cold_executes_consumer": True,
                    "exact_rerun_skips_both_commands": True,
                    "deleted_outputs_hydrate_locally_without_commands": True,
                    "fresh_workspace_hydrates_outputs_without_commands": True,
                    "fresh_workspace_hydrates_execution_logs": True,
                    "product_input_change_executes_producer_and_consumer": True,
                    "release_input_change_executes_only_consumer": True,
                },
                "execution_counts": {
                    "first_workspace_after_hydration": {
                        "product": count(first, "product"),
                        "publication": count(first, "publication"),
                    },
                    "fresh_workspace_final": {
                        "product": count(second, "product"),
                        "publication": count(second, "publication"),
                    },
                },
                "runs": {
                    "cold": cold,
                    "exact_rerun": exact,
                    "local_hydration": hydrate,
                    "fresh_workspace_hydration": fresh,
                    "changed_product": changed_product,
                    "changed_release": changed_release,
                },
            }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(
        "PASS moon orchestration: cold execution, exact cache hit, local/fresh hydration, "
        "evidence restore, producer/downstream invalidation, release-only selection"
    )


if __name__ == "__main__":
    main()
