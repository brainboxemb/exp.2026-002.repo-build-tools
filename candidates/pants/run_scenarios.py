#!/usr/bin/env python3
"""Run the neutral affected-impact scenarios through Pants."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "candidates" / "pants"
FIXTURE = ROOT / "fixture"
WORKSPACE = FIXTURE / "workspace"
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
    shutil.copy2(CANDIDATE / "pants.toml", path / "pants.toml")
    shutil.copy2(CANDIDATE / "BUILD.fixture", path / "BUILD")
    shutil.copytree(CANDIDATE / "pants-plugins", path / "pants-plugins")
    (path / ".gitignore").write_text(".pants.d/\ndist/\n.cache/\n", encoding="utf-8")

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
    capabilities: set[str] = set()
    addresses: list[str] = []
    for target in data:
        addresses.append(str(target.get("address", "")))
        for tag in target.get("tags", []) or []:
            if isinstance(tag, str) and tag.startswith("cap:"):
                capabilities.add(tag.removeprefix("cap:"))
    return sorted(capabilities), sorted(addresses)


def query(pants: str, path: Path, dependents: str) -> dict:
    argv = [
        pants,
        "--changed-since=HEAD~1",
        f"--changed-dependents={dependents}",
        "peek",
    ]
    start = time.perf_counter()
    result = run(argv, path)
    elapsed = time.perf_counter() - start
    capabilities, addresses = extract_capabilities(result.stdout)
    return {
        "command": argv[1:],
        "seconds": round(elapsed, 4),
        "capabilities": capabilities,
        "addresses": addresses,
        "stderr": result.stderr,
    }


def run_scenario(pants: str, scenario: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"pants-{scenario['id']}-") as temp:
        repo = Path(temp)
        init_repo(repo)
        mutate(repo, scenario)

        direct = query(pants, repo, "direct")
        affected = query(pants, repo, "transitive")

        expected_direct = sorted(scenario["expected_direct"])
        expected_affected = sorted(scenario["expected_affected"])
        passed = direct["capabilities"] == expected_direct and affected["capabilities"] == expected_affected

        return {
            "id": scenario["id"],
            "changed_paths": scenario["changed_paths"],
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
    parser.add_argument("--pants", default="pants")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    results = []
    for scenario in SCENARIOS:
        result = run_scenario(args.pants, scenario)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"{status} {result['id']}: "
            f"direct={result['actual_direct']} affected={result['actual_affected']}"
        )

    payload = {
        "candidate": "pants",
        "model": "custom-source-owning-capability-target",
        "pants_version": "2.33.1",
        "scie_pants_version": "0.13.2",
        "platform": "linux-x86_64",
        "scenario_count": len(results),
        "passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    failures = [result for result in results if not result["passed"]]
    if failures:
        raise SystemExit(f"{len(failures)} Pants scenario(s) failed")


if __name__ == "__main__":
    main()
