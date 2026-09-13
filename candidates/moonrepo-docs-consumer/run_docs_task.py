#!/usr/bin/env python3
"""Experiment-only adapters for real engineering-documentation producers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path.cwd()
STATE = ROOT / ".experiment-state"

TASKS = {
    "diagrams": {
        "task": "docs.diagrams",
        "owner": "eng-docs",
        "action": "diagrams",
        "evidence": ROOT / "evidence/docs-diagrams",
        "cleanup": [ROOT / "bld/docs/architecture"],
        "commands": [
            ["eng-docs", "diagrams", "--source", "docs/_diagrams", "--theme", "docs/_diagram-theme/default.yaml", "--out", "bld/docs/architecture"],
            [sys.executable, "tools/generate_architecture_diagrams.py"],
            [sys.executable, "tools/generate_timing_detail_diagrams.py"],
            [sys.executable, "tools/generate_data_display_diagrams.py"],
            [sys.executable, "tools/generate_system_model_diagrams.py"],
        ],
    },
    "planning": {
        "task": "docs.planning",
        "owner": "docs",
        "action": "planning",
        "evidence": ROOT / "evidence/docs-planning",
        "cleanup": [ROOT / "bld/docs/planning"],
        "commands": [
            [sys.executable, "tools/generate_sip_planning.py"],
            [sys.executable, "tools/generate_sip_step_pdfs.py"],
            [sys.executable, "tools/generate_sip_manager_roadmap.py"],
        ],
    },
    "assemble": {
        "task": "docs.assemble",
        "owner": "eng-docs",
        "action": "assemble",
        "evidence": ROOT / "evidence/docs-assemble",
        "cleanup": [
            ROOT / "bld/docs/documents",
            ROOT / "bld/docs/assets",
            ROOT / "bld/docs/README.md",
        ],
        "commands": [[sys.executable, "tools/generate_documents.py"]],
    },
}


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def run_command(argv: list[str], log) -> None:
    rendered = " ".join(argv)
    log.write(f"\n> {rendered}\n")
    log.flush()
    print(f"> {rendered}")
    proc = subprocess.Popen(
        argv,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
        log.write(line)
    code = proc.wait()
    log.flush()
    if code:
        raise RuntimeError(f"command failed ({code}): {rendered}")


def validate_diagrams() -> dict:
    root = ROOT / "bld/docs/architecture"
    if not root.is_dir():
        raise RuntimeError("architecture output directory missing")
    for path in sorted(root.glob("*.drawio")) + sorted(root.glob("*.svg")):
        ET.parse(path)
    required = [
        root / "system-overview.svg",
        root / "system-overview.drawio",
        root / "layered-architecture.svg",
        root / "runtime-dispatch-process.svg",
    ]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"required diagram output missing: {path}")
    return {"file_count": sum(1 for path in root.iterdir() if path.is_file())}


def valid_pdf(path: Path) -> None:
    data = path.read_bytes()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
        raise RuntimeError(f"invalid PDF: {path}")


def validate_planning() -> dict:
    root = ROOT / "bld/docs/planning"
    required = [
        root / "README.md",
        root / "sip-roadmap.svg",
        root / "sip-roadmap.pdf",
        root / "roadmap/sip-roadmap-1.svg",
        root / "roadmap/sip-roadmap-4.svg",
        root / "steps/step-02.svg",
        root / "steps/step-02.pdf",
    ]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"required planning output missing: {path}")
    ET.parse(root / "sip-roadmap.svg")
    for path in sorted((root / "roadmap").glob("*.svg")):
        ET.parse(path)
    for path in sorted((root / "steps").glob("*.svg")):
        ET.parse(path)
    valid_pdf(root / "sip-roadmap.pdf")
    for path in sorted((root / "steps").glob("*.pdf")):
        valid_pdf(path)
    return {"file_count": sum(1 for path in root.rglob("*") if path.is_file())}


def validate_assemble() -> dict:
    root = ROOT / "bld/docs"
    required = [
        root / "README.md",
        root / "documents/README.md",
        root / "documents/software-document-set.md",
        root / "documents/architecture-book.md",
        root / "documents/12-SDE-software-development-environment.md",
        root / "documents/13-SDE-java-build-test-toolchain.md",
        root / "documents/31-01-SAD-timing-application-architecture.md",
        root / "documents/31-01-SDD-02-java-component-design.md",
        root / "documents/50-SVP-software-verification-plan.md",
        root / "assets/architecture/system-overview.svg",
        root / "assets/architecture/system-overview.drawio",
    ]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"required assembled output missing: {path}")
    architecture_book = (root / "documents/architecture-book.md").read_text(encoding="utf-8")
    active_marker = (
        "**Source document:** [31-01-SDD-02-java-component-design.md]"
        "(./31-01-SDD-02-java-component-design.md)"
    )
    deferred_markers = [
        "**Source document:** [31-01-SDD-01-data-and-display-design.md]"
        "(./31-01-SDD-01-data-and-display-design.md)",
        "**Source document:** [31-01-SDD-03-backoffice-transport-design.md]"
        "(./31-01-SDD-03-backoffice-transport-design.md)",
    ]
    if active_marker not in architecture_book:
        raise RuntimeError("active SDD section missing from architecture book")
    if any(marker in architecture_book for marker in deferred_markers):
        raise RuntimeError("deferred SDD section unexpectedly present in architecture book")
    return {
        "document_count": sum(1 for path in (root / "documents").glob("*.md")),
        "asset_count": sum(1 for path in (root / "assets/architecture").iterdir() if path.is_file()),
    }


def validate(kind: str) -> dict:
    if kind == "diagrams":
        return validate_diagrams()
    if kind == "planning":
        return validate_planning()
    return validate_assemble()


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in TASKS:
        raise SystemExit("usage: run_docs_task.py diagrams|planning|assemble")
    kind = sys.argv[1]
    cfg = TASKS[kind]
    task_id = cfg["task"]
    evidence: Path = cfg["evidence"]
    evidence.mkdir(parents=True, exist_ok=True)
    log_path = evidence / "execution.log"
    json_path = evidence / "execution.json"
    log_path.unlink(missing_ok=True)
    json_path.unlink(missing_ok=True)

    STATE.mkdir(exist_ok=True)
    counter_path = STATE / f"{task_id.replace('.', '-')}.count"
    count = int(counter_path.read_text(encoding="utf-8")) if counter_path.is_file() else 0
    count += 1
    counter_path.write_text(f"{count}\n", encoding="utf-8")

    for path in cfg["cleanup"]:
        remove(path)

    source_sha = git("rev-parse", "HEAD")
    tool_stamp = ROOT / ".experiment/tool-eng-docs.sha"
    tool_sha = tool_stamp.read_text(encoding="utf-8").strip() if tool_stamp.is_file() else ""
    task_hash = os.environ.get("MOON_TASK_HASH", "")
    status = "success"
    error = ""
    details: dict = {}

    with log_path.open("w", encoding="utf-8") as log:
        header = [
            f"Documentation task: {task_id}",
            f"source_sha={source_sha}",
            f"tool_eng_docs_sha={tool_sha}",
            f"moon_task_hash={task_hash}",
            f"invocation={count}",
        ]
        for line in header:
            print(line)
            log.write(line + "\n")
        try:
            for command in cfg["commands"]:
                run_command(command, log)
            details = validate(kind)
        except Exception as exc:  # evidence must survive a failed proof
            status = "failed"
            error = str(exc)
            print(f"ERROR: {error}")
            log.write(f"\nERROR: {error}\n")

    payload = {
        "schema": "repo-build-tools.execution-evidence",
        "schema_version": 1,
        "task": task_id,
        "owner": cfg["owner"],
        "action": cfg["action"],
        "status": status,
        "source_sha": source_sha,
        "tool_eng_docs_sha": tool_sha or None,
        "moon_task_hash": task_hash,
        "invocation": count,
        "log": "execution.log",
        "details": details,
    }
    if error:
        payload["error"] = error
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if status != "success":
        raise SystemExit(error or "documentation task failed")


if __name__ == "__main__":
    main()
