#!/usr/bin/env python3
"""Minimal repository affected-capability query for the neutral experiment model."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import deque
from pathlib import Path


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"git {' '.join(args)} failed ({result.returncode})\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result.stdout


def normalize_path(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def glob_regex(pattern: str) -> re.Pattern[str]:
    """Translate the small cross-platform glob contract used by the fixture.

    `*` does not cross a slash. `**` does. `**/` may match zero or more path
    segments, so `docs/**/*.md` also matches `docs/guide.md`.
    """

    pattern = normalize_path(pattern)
    pieces: list[str] = ["^"]
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                index += 2
                if index < len(pattern) and pattern[index] == "/":
                    pieces.append("(?:.*/)?")
                    index += 1
                else:
                    pieces.append(".*")
                continue
            pieces.append("[^/]*")
        elif char == "?":
            pieces.append("[^/]")
        else:
            pieces.append(re.escape(char))
        index += 1
    pieces.append("$")
    return re.compile("".join(pieces))


def matches(path: str, patterns: list[str]) -> bool:
    normalized = normalize_path(path)
    return any(glob_regex(pattern).match(normalized) for pattern in patterns)


def changed_paths(base: str, head: str) -> list[str]:
    output = run_git("diff", "--name-only", "--no-ext-diff", base, head, "--")
    return sorted(
        normalize_path(line.strip())
        for line in output.splitlines()
        if line.strip()
    )


def direct_capabilities(model: dict, changed: list[str]) -> set[str]:
    capabilities = model["capabilities"]
    global_inputs = model.get("global_inputs", [])

    if any(matches(path, global_inputs) for path in changed):
        return set(capabilities)

    direct: set[str] = set()
    for capability, spec in capabilities.items():
        patterns = spec.get("inputs", [])
        if any(matches(path, patterns) for path in changed):
            direct.add(capability)
    return direct


def downstream_closure(model: dict, direct: set[str]) -> set[str]:
    reverse: dict[str, set[str]] = {name: set() for name in model["capabilities"]}
    for capability, spec in model["capabilities"].items():
        for dependency in spec.get("depends_on", []):
            reverse.setdefault(dependency, set()).add(capability)

    affected = set(direct)
    queue: deque[str] = deque(sorted(direct))
    while queue:
        current = queue.popleft()
        for downstream in sorted(reverse.get(current, ())):
            if downstream not in affected:
                affected.add(downstream)
                queue.append(downstream)
    return affected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--downstream", choices=("none", "deep"), default="deep")
    args = parser.parse_args()

    model = json.loads(args.model.read_text(encoding="utf-8"))
    changed = changed_paths(args.base, args.head)
    direct = direct_capabilities(model, changed)
    selected = direct if args.downstream == "none" else downstream_closure(model, direct)

    print(
        json.dumps(
            {
                "changed_paths": changed,
                "capabilities": sorted(selected),
                "downstream": args.downstream,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
