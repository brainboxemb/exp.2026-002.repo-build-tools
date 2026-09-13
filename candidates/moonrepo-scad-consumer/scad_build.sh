#!/usr/bin/env bash
set -uo pipefail

ROOT="$(pwd)"
EVIDENCE="$ROOT/evidence/scad-build"
STATE="$ROOT/.experiment-state"
mkdir -p "$EVIDENCE/domain" "$STATE"
rm -f "$EVIDENCE/execution.log" "$EVIDENCE/execution.json"

COUNTER="$STATE/scad-build.count"
COUNT=0
if [[ -f "$COUNTER" ]]; then COUNT="$(cat "$COUNTER")"; fi
COUNT=$((COUNT + 1))
printf '%s\n' "$COUNT" > "$COUNTER"

SOURCE_SHA="$(git rev-parse HEAD)"
TOOL_SHA="$(git -C tools/tool.scad-project rev-parse HEAD)"
TASK_HASH="${MOON_TASK_HASH:-}"
export SCAD_PROJECT_SOURCE_SHA="$SOURCE_SHA"
export SCAD_PROJECT_TOOL_SHA="$TOOL_SHA"
export SCAD_PROJECT_WORKFLOW_VERSION="moon-r1c"
export SCAD_TOOLCHAIN_IMAGE="ghcr.io/brainboxemb/scad-toolchain:v0.4.1"
export SCAD_TOOLCHAIN_VERSION="v0.4.1"

set +e
(
  set -e
  echo "SCAD Build under moon"
  echo "source_sha=$SOURCE_SHA"
  echo "tool_sha=$TOOL_SHA"
  echo "moon_task_hash=$TASK_HASH"
  echo "invocation=$COUNT"
  scad-toolchain-info
  for command in tooling-check config-lint externals-check docs-lint design-lint design-build build build-index publication-info-build; do
    echo
    echo "> scad-project $command"
    bash ./tools/tool.scad-project/scad-project.sh "$command"
  done
) > >(tee "$EVIDENCE/execution.log") 2>&1
STATUS=$?
set -e

for report in \
  .cache/scad-project/state/last-build.json \
  .cache/scad-project/state/last-design-build.json; do
  if [[ -f "$report" ]]; then
    cp "$report" "$EVIDENCE/domain/$(basename "$report")"
  fi
done

STATUS="$STATUS" SOURCE_SHA="$SOURCE_SHA" TOOL_SHA="$TOOL_SHA" TASK_HASH="$TASK_HASH" COUNT="$COUNT" \
python3 - <<'PY'
import json
import os
from pathlib import Path
payload = {
    "schema": "repo-build-tools.execution-evidence",
    "schema_version": 1,
    "task": "scad.build",
    "owner": "scad",
    "action": "build",
    "status": "success" if os.environ["STATUS"] == "0" else "failed",
    "exit_code": int(os.environ["STATUS"]),
    "source_sha": os.environ["SOURCE_SHA"],
    "tool_scad_project_sha": os.environ["TOOL_SHA"],
    "moon_task_hash": os.environ["TASK_HASH"],
    "invocation": int(os.environ["COUNT"]),
    "log": "execution.log",
    "domain_evidence": sorted(p.name for p in Path("evidence/scad-build/domain").glob("*.json")),
}
Path("evidence/scad-build/execution.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

exit "$STATUS"
