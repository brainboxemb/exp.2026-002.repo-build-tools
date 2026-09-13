#!/usr/bin/env python3
"""Run the neutral affected-impact scenarios through moonrepo."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "candidates" / "moonrepo"
FIXTURE = ROOT / "fixture"
WORKSPACE = FIXTURE / "workspace"
SCENARIOS = json.loads((FIXTURE / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]


def run(
    argv: list[str],
    cwd: Path,
    *,
    check: bool = True,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        input=stdin,
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(argv)}\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result


def init_repo(path: Path) -> None:
    shutil.copytree(WORKSPACE, path, dirs_exist_ok=True)
    shutil.copytree(CANDIDATE / ".moon", path / ".moon")
    shutil.copy2(CANDIDATE / "moon.yml", path / "moon.yml")
    (path / ".gitignore").write_text(".moon/cache/\n.moon/docker/\n", encoding="utf-8")

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


def extract_capabilities(stdout: str) -> tuple[list[str], list[str]]:
    data = json.loads(stdout)
    tasks = data.get("tasks", {})
    if not isinstance(tasks, dict):
        raise RuntimeError(f"moon query returned unexpected tasks shape: {type(tasks)!r}")

    # `query tasks` groups tasks by project. Keep the parser tolerant of a flat
    # target map as well so evidence remains useful if moon changes presentation.
    raw_targets: list[str] = []
    capabilities: set[str] = set()

    if any(":" in str(key) for key in tasks):
        for target in sorted(str(key) for key in tasks):
            raw_targets.append(target)
            capabilities.add(target.split(":", 1)[-1])
    else:
        for project_id, project_tasks in tasks.items():
            if not isinstance(project_tasks, dict):
                continue
            for task_id in sorted(str(key) for key in project_tasks):
                raw_targets.append(f"{project_id}:{task_id}")
                capabilities.add(task_id)

    return sorted(capabilities), sorted(raw_targets)


def changed_files(moon: str, path: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            moon,
            "query",
            "changed-files",
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
        ],
        path,
    )


def query(moon: str, path: Path, downstream: str, changed_json: str) -> dict:
    argv = [
        moon,
        "query",
        "tasks",
        "--affected",
        "--upstream",
        "none",
        "--downstream",
        downstream,
    ]
    start = time.perf_counter()
    result = run(argv, path, stdin=changed_json)
    elapsed = time.perf_counter() - start
    capabilities, targets = extract_capabilities(result.stdout)
    return {
        "command": argv[1:],
        "seconds": round(elapsed, 4),
        "capabilities": capabilities,
        "targets": targets,
        "stderr": result.stderr,
    }


def run_scenario(moon: str, scenario: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"moon-{scenario['id']}-") as temp:
        repo = Path(temp)
        init_repo(repo)
        mutate(repo, scenario)

        changed = changed_files(moon, repo)
        changed_payload = json.loads(changed.stdout)
        changed_paths = sorted(str(path) for path in changed_payload.get("files", []))

        direct = query(moon, repo, "none", changed.stdout)
        affected = query(moon, repo, "deep", changed.stdout)

        expected_direct = sorted(scenario["expected_direct"])
        expected_affected = sorted(scenario["expected_affected"])
        passed = (
            changed_paths == sorted(scenario["changed_paths"])
            and direct["capabilities"] == expected_direct
            and affected["capabilities"] == expected_affected
        )

        return {
            "id": scenario["id"],
            "changed_paths": scenario["changed_paths"],
            "moon_changed_paths": changed_paths,
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
    parser.add_argument("--moon", default="moon")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    version = run([args.moon, "--version"], ROOT).stdout.strip()
    results = []
    for scenario in SCENARIOS:
        result = run_scenario(args.moon, scenario)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"{status} {result['id']}: "
            f"changed={result['moon_changed_paths']} "
            f"direct={result['actual_direct']} affected={result['actual_affected']}"
        )

    payload = {
        "candidate": "moonrepo",
        "moon_version": version,
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
        raise SystemExit(f"{len(failures)} moonrepo scenario(s) failed")


if __name__ == "__main__":
    main()
