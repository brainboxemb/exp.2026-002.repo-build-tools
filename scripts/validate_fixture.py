#!/usr/bin/env python3
"""Validate only the candidate-neutral experiment fixture structure."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "fixture" / "capability-model.json"
SCENARIOS_PATH = ROOT / "fixture" / "scenarios.json"
WORKSPACE = ROOT / "fixture" / "workspace"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def downstream_closure(direct: set[str], capabilities: dict[str, dict]) -> set[str]:
    dependents: dict[str, set[str]] = defaultdict(set)
    for name, spec in capabilities.items():
        for dependency in spec.get("depends_on", []):
            dependents[dependency].add(name)

    affected = set(direct)
    queue = deque(sorted(direct))
    while queue:
        current = queue.popleft()
        for dependent in sorted(dependents.get(current, ())):
            if dependent not in affected:
                affected.add(dependent)
                queue.append(dependent)
    return affected


def main() -> None:
    model = load(MODEL_PATH)
    scenarios = load(SCENARIOS_PATH)

    assert model.get("schema_version") == 1
    assert scenarios.get("schema_version") == 1

    capabilities = model.get("capabilities")
    assert isinstance(capabilities, dict) and capabilities, "capabilities must be a non-empty object"
    names = set(capabilities)

    for name, spec in capabilities.items():
        dependencies = spec.get("depends_on", [])
        assert isinstance(dependencies, list), f"{name}: depends_on must be a list"
        unknown = set(dependencies) - names
        assert not unknown, f"{name}: unknown dependencies: {sorted(unknown)}"
        assert name not in dependencies, f"{name}: self-dependency is invalid"
        assert isinstance(spec.get("inputs", []), list), f"{name}: inputs must be a list"

    # Detect dependency cycles by repeatedly taking graph closure from each node.
    for start in names:
        seen: set[str] = set()
        queue = deque(capabilities[start].get("depends_on", []))
        while queue:
            current = queue.popleft()
            assert current != start, f"dependency cycle reaches {start}"
            if current in seen:
                continue
            seen.add(current)
            queue.extend(capabilities[current].get("depends_on", []))

    scenario_list = scenarios.get("scenarios")
    assert isinstance(scenario_list, list) and scenario_list, "scenarios must be a non-empty list"
    ids: set[str] = set()

    for scenario in scenario_list:
        scenario_id = scenario["id"]
        assert scenario_id not in ids, f"duplicate scenario id: {scenario_id}"
        ids.add(scenario_id)

        operation = scenario.get("operation", "modify")
        assert operation in {"modify", "delete"}, (
            f"{scenario_id}: operation must be 'modify' or 'delete', got {operation!r}"
        )

        changed_paths = scenario.get("changed_paths", [])
        assert changed_paths, f"{scenario_id}: changed_paths must not be empty"
        for relative in changed_paths:
            path = WORKSPACE / relative
            assert path.exists(), f"{scenario_id}: fixture path does not exist: {relative}"
            assert path.is_file(), f"{scenario_id}: fixture mutation path must be a file: {relative}"

        direct = set(scenario.get("expected_direct", []))
        affected = set(scenario.get("expected_affected", []))
        assert direct <= names, f"{scenario_id}: unknown direct capability"
        assert affected <= names, f"{scenario_id}: unknown affected capability"
        assert direct <= affected, f"{scenario_id}: direct capabilities must be affected"

        expected_closure = downstream_closure(direct, capabilities)
        assert affected == expected_closure, (
            f"{scenario_id}: affected set must equal declared downstream closure; "
            f"expected {sorted(expected_closure)}, got {sorted(affected)}"
        )

    print(
        f"fixture OK: {len(capabilities)} capabilities, "
        f"{len(scenario_list)} scenarios, schema v1"
    )


if __name__ == "__main__":
    main()
