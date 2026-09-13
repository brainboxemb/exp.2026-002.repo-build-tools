#!/usr/bin/env python3
"""Run the neutral affected-impact scenarios through native-thin."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "candidates" / "native-thin"
FIXTURE = ROOT / "fixture"
WORKSPACE = FIXTURE / "workspace"
MODEL = FIXTURE / "capability-model.json"
SCENARIOS = json.loads((FIXTURE / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]


def run(argv: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(argv)}\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result


def init_repo(path: Path) -> None:
    shutil.copytree(WORKSPACE, path, dirs_exist_ok=True)
    shutil.copy2(MODEL, path / "capability-model.json")
    shutil.copy2(CANDIDATE / "affected.py", path / "affected.py")
    (path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")

    run(["git", "init", "-b", "main"], path)
    run(["git", "config", "user.name", "repo-build-tools-experiment"], path)
    run(["git", "config", "user.email", "experiment@example.invalid"], path)
    run(["git", "add", "."], path)
    run(["git", "commit", "-m", "baseline"], path)


def mutate(path: Path, scenario: dict) -> None:
    for relative in scenario["changed_paths"]:
        target = path / relative
        with target.open("a", encoding="utf-8") as handle:
            handle.write(f"\nscenario={scenario['id']}\n")
    run(["git", "add", "."], path)
    run(["git", "commit", "-m", scenario["id"]], path)


def query(path: Path, downstream: str) -> dict:
    argv = [
        sys.executable,
        "affected.py",
        "--model",
        "capability-model.json",
        "--base",
        "HEAD~1",
        "--head",
        "HEAD",
        "--downstream",
        downstream,
    ]
    start = time.perf_counter()
    result = run(argv, path)
    elapsed = time.perf_counter() - start
    payload = json.loads(result.stdout)
    return {
        "command": argv[1:],
        "seconds": round(elapsed, 6),
        "changed_paths": payload["changed_paths"],
        "capabilities": payload["capabilities"],
        "stderr": result.stderr,
    }


def run_scenario(scenario: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"native-{scenario['id']}-") as temp:
        repo = Path(temp)
        init_repo(repo)
        mutate(repo, scenario)

        direct = query(repo, "none")
        affected = query(repo, "deep")

        expected_direct = sorted(scenario["expected_direct"])
        expected_affected = sorted(scenario["expected_affected"])
        passed = (
            direct["changed_paths"] == sorted(scenario["changed_paths"])
            and direct["capabilities"] == expected_direct
            and affected["capabilities"] == expected_affected
        )

        return {
            "id": scenario["id"],
            "changed_paths": scenario["changed_paths"],
            "native_changed_paths": direct["changed_paths"],
            "expected_direct": expected_direct,
            "actual_direct": direct["capabilities"],
            "expected_affected": expected_affected,
            "actual_affected": affected["capabilities"],
            "passed": passed,
            "direct_query": direct,
            "affected_query": affected,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    results = []
    for scenario in SCENARIOS:
        result = run_scenario(scenario)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"{status} {result['id']}: changed={result['native_changed_paths']} "
            f"direct={result['actual_direct']} affected={result['actual_affected']}"
        )

    payload = {
        "candidate": "native-thin",
        "python_version": sys.version.split()[0],
        "platform": args.platform,
        "scenario_count": len(results),
        "passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    failures = [result for result in results if not result["passed"]]
    if failures:
        raise SystemExit(f"{len(failures)} native-thin scenario(s) failed")


if __name__ == "__main__":
    main()
