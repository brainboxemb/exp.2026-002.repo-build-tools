#!/usr/bin/env python3
"""Qualify Moon against the real engineering-documentation producer graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "candidates" / "moonrepo-docs-consumer"
CONSUMER_REPO = "https://github.com/brainboxemb/2026-010-01.meta.event-timing-software.git"
CONSUMER_SHA = "33d2a5bcec547694c1541da52563e26b08c3ded0"
ENG_DOCS_SHA = "184e030a188385451a3392a8c43b081ae18c0650"


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


def init_workspace(path: Path) -> None:
    run(["git", "clone", "--recurse-submodules", "--no-tags", CONSUMER_REPO, str(path)], ROOT)
    run(["git", "checkout", "--detach", CONSUMER_SHA], path)
    run(["git", "submodule", "update", "--init"], path)
    run(["git", "config", "user.name", "repo-build-tools-experiment"], path)
    run(["git", "config", "user.email", "experiment@example.invalid"], path)

    actual_tool = run(["git", "-C", "tools/tool.eng-docs", "rev-parse", "HEAD"], path).stdout.strip()
    require(actual_tool == ENG_DOCS_SHA, f"unexpected tool.eng-docs SHA: {actual_tool}")

    shutil.copytree(CANDIDATE / ".moon", path / ".moon", dirs_exist_ok=True)
    shutil.copy2(CANDIDATE / "moon.yml", path / "moon.yml")
    experiment = path / ".experiment"
    experiment.mkdir(exist_ok=True)
    shutil.copy2(CANDIDATE / "run_docs_task.py", experiment / "run_docs_task.py")
    (experiment / "tool-eng-docs.sha").write_text(ENG_DOCS_SHA + "\n", encoding="utf-8")

    exclude = path / ".git" / "info" / "exclude"
    with exclude.open("a", encoding="utf-8") as handle:
        handle.write("\n.moon/\nmoon.yml\n.experiment/\n.experiment-state/\nbld/\nevidence/\n")


def install_dependencies(workspace: Path) -> None:
    run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(workspace / "tools/requirements-docs.txt")],
        ROOT,
    )
    run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", str(workspace / "tools/tool.eng-docs")],
        ROOT,
    )


def run_assemble(moon: str, path: Path) -> dict:
    result = run([moon, "run", "consumer:docs.assemble", "--log", "info"], path)
    return {"stdout": result.stdout, "stderr": result.stderr}


def count(path: Path, task: str) -> int:
    file = path / ".experiment-state" / f"{task.replace('.', '-')}.count"
    return int(file.read_text(encoding="utf-8")) if file.is_file() else 0


def counts(path: Path) -> dict[str, int]:
    return {task: count(path, task) for task in ("docs.diagrams", "docs.planning", "docs.assemble")}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(path: Path) -> dict[str, str]:
    required = [
        "bld/docs/architecture/system-overview.svg",
        "bld/docs/architecture/system-overview.drawio",
        "bld/docs/planning/sip-roadmap.svg",
        "bld/docs/planning/sip-roadmap.pdf",
        "bld/docs/planning/steps/step-02.pdf",
        "bld/docs/documents/software-document-set.md",
        "bld/docs/documents/architecture-book.md",
        "bld/docs/assets/architecture/system-overview.svg",
        "bld/docs/README.md",
        "evidence/docs-diagrams/execution.json",
        "evidence/docs-diagrams/execution.log",
        "evidence/docs-planning/execution.json",
        "evidence/docs-planning/execution.log",
        "evidence/docs-assemble/execution.json",
        "evidence/docs-assemble/execution.log",
    ]
    missing = [relative for relative in required if not (path / relative).is_file()]
    if missing:
        raise RuntimeError(f"missing docs outputs/evidence: {missing}")
    return {relative: sha256(path / relative) for relative in required}


def evidence(path: Path, task: str) -> dict:
    return json.loads((path / f"evidence/{task.replace('.', '-')}/execution.json").read_text(encoding="utf-8"))


def copy_portable_cache(source: Path, destination: Path) -> list[str]:
    copied = []
    for name in ("hashes", "outputs"):
        src = source / ".moon" / "cache" / name
        require(src.is_dir(), f"moon portable cache directory missing: {src}")
        dst = destination / ".moon" / "cache" / name
        shutil.copytree(src, dst, dirs_exist_ok=True)
        copied.append(name)
    return copied


def commit(path: Path, files: list[str], message: str) -> str:
    run(["git", "add", *files], path)
    run(["git", "commit", "-m", message], path)
    return run(["git", "rev-parse", "HEAD"], path).stdout.strip()


def mutate_authored_markdown(path: Path) -> None:
    target = path / "docs/03-domain-baseline.md"
    with target.open("a", encoding="utf-8") as handle:
        handle.write("\n<!-- R1e authored-document mutation -->\n")


def mutate_diagram(path: Path) -> None:
    target = path / "docs/_diagrams/system-overview.yaml"
    text = target.read_text(encoding="utf-8")
    old = "title: Headless timing application — component and interface overview"
    new = "title: Headless timing application — component and interface overview (R1e)"
    require(old in text, "system-overview title not found")
    target.write_text(text.replace(old, new), encoding="utf-8")


def mutate_planning(path: Path) -> None:
    target = path / "docs/_data/sip-manager-roadmap.yaml"
    text = target.read_text(encoding="utf-8")
    old = "Architecture baseline for SI-01, SI-02 and SI-03"
    new = "Architecture baseline for SI-01/SI-02/SI-03"
    require(old in text, "manager roadmap proof text not found")
    target.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--moon", default="moon")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    moon_version = run([args.moon, "--version"], ROOT).stdout.strip()

    with tempfile.TemporaryDirectory(prefix="moon-docs-source-") as first_temp:
        first = Path(first_temp)
        init_workspace(first)
        install_dependencies(first)

        baseline_head = run(["git", "rev-parse", "HEAD"], first).stdout.strip()
        cold = run_assemble(args.moon, first)
        require(counts(first) == {"docs.diagrams": 1, "docs.planning": 1, "docs.assemble": 1}, f"unexpected cold counts: {counts(first)}")
        cold_snapshot = snapshot(first)
        cold_evidence = {task: evidence(first, task) for task in ("docs.diagrams", "docs.planning", "docs.assemble")}
        for task, item in cold_evidence.items():
            require(item["status"] == "success", f"cold {task} failed")
            require(item["source_sha"] == baseline_head, f"cold {task} source SHA mismatch")
            require(bool(item.get("moon_task_hash")), f"cold {task} missing Moon task hash")

        exact = run_assemble(args.moon, first)
        require(counts(first) == {"docs.diagrams": 1, "docs.planning": 1, "docs.assemble": 1}, "exact rerun unexpectedly executed docs tasks")
        require(snapshot(first) == cold_snapshot, "exact rerun changed cached docs output/evidence")

        shutil.rmtree(first / "bld/docs")
        shutil.rmtree(first / "evidence")
        local_hydration = run_assemble(args.moon, first)
        require(counts(first) == {"docs.diagrams": 1, "docs.planning": 1, "docs.assemble": 1}, "local hydration executed docs tasks")
        require(snapshot(first) == cold_snapshot, "local hydration did not restore exact docs output/evidence")

        with tempfile.TemporaryDirectory(prefix="moon-docs-fresh-") as second_temp:
            second = Path(second_temp)
            init_workspace(second)
            copied_cache = copy_portable_cache(first, second)
            fresh = run_assemble(args.moon, second)
            require(counts(second) == {"docs.diagrams": 0, "docs.planning": 0, "docs.assemble": 0}, "fresh hydration executed docs tasks")
            require(snapshot(second) == cold_snapshot, "fresh hydration did not restore exact docs output/evidence")

        mutate_authored_markdown(first)
        authored_head = commit(first, ["docs/03-domain-baseline.md"], "R1e authored document mutation")
        before_authored_set = sha256(first / "bld/docs/documents/software-document-set.md")
        authored = run_assemble(args.moon, first)
        require(counts(first) == {"docs.diagrams": 1, "docs.planning": 1, "docs.assemble": 2}, f"authored Markdown selected wrong tasks: {counts(first)}")
        require(sha256(first / "bld/docs/documents/software-document-set.md") != before_authored_set, "authored Markdown did not change assembled document set")
        require(evidence(first, "docs.assemble")["source_sha"] == authored_head, "assemble producer revision mismatch after authored Markdown")
        require(evidence(first, "docs.diagrams")["source_sha"] == baseline_head, "cached diagrams lost original producer revision")
        require(evidence(first, "docs.planning")["source_sha"] == baseline_head, "cached planning lost original producer revision")

        before_diagram = sha256(first / "bld/docs/architecture/system-overview.svg")
        mutate_diagram(first)
        diagram_head = commit(first, ["docs/_diagrams/system-overview.yaml"], "R1e diagram source mutation")
        diagram = run_assemble(args.moon, first)
        require(counts(first) == {"docs.diagrams": 2, "docs.planning": 1, "docs.assemble": 3}, f"diagram mutation selected wrong tasks: {counts(first)}")
        require(sha256(first / "bld/docs/architecture/system-overview.svg") != before_diagram, "diagram source mutation did not change diagram output")
        require(evidence(first, "docs.diagrams")["source_sha"] == diagram_head, "diagram producer revision mismatch")
        require(evidence(first, "docs.planning")["source_sha"] == baseline_head, "diagram mutation unexpectedly replaced planning provenance")

        before_planning = sha256(first / "bld/docs/planning/sip-roadmap.svg")
        mutate_planning(first)
        planning_head = commit(first, ["docs/_data/sip-manager-roadmap.yaml"], "R1e planning data mutation")
        planning = run_assemble(args.moon, first)
        require(counts(first) == {"docs.diagrams": 2, "docs.planning": 2, "docs.assemble": 4}, f"planning mutation selected wrong tasks: {counts(first)}")
        require(sha256(first / "bld/docs/planning/sip-roadmap.svg") != before_planning, "planning mutation did not change roadmap output")
        require(evidence(first, "docs.planning")["source_sha"] == planning_head, "planning producer revision mismatch")

        final_producers = {task: evidence(first, task)["source_sha"] for task in ("docs.diagrams", "docs.planning", "docs.assemble")}
        require(len(set(final_producers.values())) >= 2, "proof did not preserve independent task producer revisions")

        payload = {
            "candidate": "moonrepo-docs-consumer",
            "moon_version": moon_version,
            "consumer_repository": "brainboxemb/2026-010-01.meta.event-timing-software",
            "consumer_sha": CONSUMER_SHA,
            "tool_eng_docs_sha": ENG_DOCS_SHA,
            "portable_cache_directories": copied_cache,
            "checks": {
                "cold_three_task_graph_executes": True,
                "exact_rerun_skips_all_producers": True,
                "deleted_outputs_hydrate_without_producers": True,
                "fresh_workspace_hydrates_outputs_and_logs": True,
                "authored_markdown_executes_only_assembly": True,
                "diagram_source_executes_diagrams_and_downstream_assembly": True,
                "planning_data_executes_planning_and_downstream_assembly": True,
                "independent_task_producer_revisions_are_preserved": True,
            },
            "execution_counts_final": counts(first),
            "revisions": {
                "baseline": baseline_head,
                "authored_markdown": authored_head,
                "diagram_source": diagram_head,
                "planning_data": planning_head,
                "final_task_producers": final_producers,
            },
            "runs": {
                "cold": cold,
                "exact_rerun": exact,
                "local_hydration": local_hydration,
                "fresh_workspace_hydration": fresh,
                "authored_markdown": authored,
                "diagram_source": diagram,
                "planning_data": planning,
            },
            "architecture_notes": [
                "diagram and planning producers have non-overlapping owned output trees and are genuine upstream dependencies of document assembly",
                "the three planning generator scripts remain one high-level task because they collaboratively own bld/docs/planning",
                "source/reference validators are CI gating concerns, not automatically artifact dependencies of assembly",
                "publication is an external side effect and remains outside the cacheable producer graph",
                "a materialized documentation snapshot may combine cached task outputs produced by different input-equivalent revisions; publication must retain per-task producer provenance plus the materialization revision",
            ],
        }

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            exported = args.output.parent / "evidence"
            if exported.exists():
                shutil.rmtree(exported)
            shutil.copytree(first / "evidence", exported / "task-evidence")
            selected = exported / "selected-output"
            selected.mkdir(parents=True, exist_ok=True)
            for relative in (
                "bld/docs/architecture/system-overview.svg",
                "bld/docs/planning/sip-roadmap.svg",
                "bld/docs/documents/software-document-set.md",
                "bld/docs/README.md",
            ):
                src = first / relative
                dst = selected / relative.replace("/", "__")
                shutil.copy2(src, dst)

    print(
        "PASS moon + real docs consumer: independent diagram/planning producers, "
        "selective assembly, hydration, and per-task producer provenance"
    )


if __name__ == "__main__":
    import sys
    main()
