#!/usr/bin/env bash
set -uo pipefail

ROOT="$(pwd)"
OUT="$ROOT/bld/java"
EVIDENCE="$ROOT/evidence/java-canonical"
STATE="$ROOT/.experiment-state"
mkdir -p "$OUT/artifacts" "$OUT/evidence/tests" "$EVIDENCE" "$STATE"
rm -rf "$OUT/artifacts" "$OUT/evidence/tests"
mkdir -p "$OUT/artifacts" "$OUT/evidence/tests"
rm -f "$EVIDENCE/execution.log" "$EVIDENCE/execution.json"

COUNTER="$STATE/java-canonical.count"
COUNT=0
if [[ -f "$COUNTER" ]]; then COUNT="$(cat "$COUNTER")"; fi
COUNT=$((COUNT + 1))
printf '%s\n' "$COUNT" > "$COUNTER"

SOURCE_SHA="$(git rev-parse HEAD)"
TOOL_SHA="$(cat .experiment/tool-java-project.sha)"
TASK_HASH="${MOON_TASK_HASH:-}"

set +e
(
  set -e
  echo "Java canonical verify under moon"
  echo "source_sha=$SOURCE_SHA"
  echo "tool_java_project_sha=$TOOL_SHA"
  echo "moon_task_hash=$TASK_HASH"
  echo "invocation=$COUNT"
  echo
  echo "> java -version"
  java -version
  echo
  echo "> ./mvnw --version"
  ./mvnw --version
  echo
  echo "> ./mvnw --batch-mode --no-transfer-progress verify"
  ./mvnw --batch-mode --no-transfer-progress verify
) > >(tee "$EVIDENCE/execution.log") 2>&1
STATUS=$?
set -e

if [[ "$STATUS" -eq 0 ]]; then
  JAR="target/template-java-project-0.1.0-SNAPSHOT.jar"
  if [[ ! -s "$JAR" ]]; then
    echo "ERROR: canonical JAR missing: $JAR" | tee -a "$EVIDENCE/execution.log" >&2
    STATUS=1
  else
    cp "$JAR" "$OUT/artifacts/"
  fi

  if [[ -d target/surefire-reports ]]; then
    cp -a target/surefire-reports/. "$OUT/evidence/tests/"
  else
    echo "ERROR: Surefire reports missing" | tee -a "$EVIDENCE/execution.log" >&2
    STATUS=1
  fi
fi

JAVA_RUNTIME="$(java -version 2>&1 | head -n 1)"
MAVEN_RUNTIME="$(./mvnw --version 2>/dev/null | head -n 1 || true)"
{
  echo "toolchain_contract=1"
  echo "source_sha=$SOURCE_SHA"
  echo "tool_java_project_sha=$TOOL_SHA"
  echo "moon_task_hash=$TASK_HASH"
  echo "java_runtime=$JAVA_RUNTIME"
  echo "maven_runtime=$MAVEN_RUNTIME"
} > "$OUT/evidence/toolchain-build-provenance.txt"
printf '%s\n' "$SOURCE_SHA" > "$OUT/source-sha.txt"

STATUS="$STATUS" SOURCE_SHA="$SOURCE_SHA" TOOL_SHA="$TOOL_SHA" TASK_HASH="$TASK_HASH" COUNT="$COUNT" \
python3 - <<'PY'
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

report_root = Path("bld/java/evidence/tests")
tests = failures = errors = skipped = 0
for path in report_root.glob("TEST-*.xml"):
    root = ET.parse(path).getroot()
    tests += int(root.attrib.get("tests", 0))
    failures += int(root.attrib.get("failures", 0))
    errors += int(root.attrib.get("errors", 0))
    skipped += int(root.attrib.get("skipped", 0))

summary = {
    "tests": tests,
    "failures": failures,
    "errors": errors,
    "skipped": skipped,
}
Path("bld/java/evidence/tests/summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
Path("bld/java/evidence/tests/README.md").write_text(
    "# Unit test report\n\n"
    f"Tests: **{tests}**  \nFailures: **{failures}**  \nErrors: **{errors}**  \nSkipped: **{skipped}**\n",
    encoding="utf-8",
)

payload = {
    "schema": "repo-build-tools.execution-evidence",
    "schema_version": 1,
    "task": "java.canonical",
    "owner": "java",
    "action": "canonical-verify",
    "status": "success" if os.environ["STATUS"] == "0" else "failed",
    "exit_code": int(os.environ["STATUS"]),
    "source_sha": os.environ["SOURCE_SHA"],
    "tool_java_project_sha": os.environ["TOOL_SHA"],
    "moon_task_hash": os.environ["TASK_HASH"],
    "invocation": int(os.environ["COUNT"]),
    "log": "execution.log",
    "domain_evidence": [
        "bld/java/evidence/toolchain-build-provenance.txt",
        "bld/java/evidence/tests/",
    ],
    "test_summary": summary,
}
Path("evidence/java-canonical/execution.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

cat > "$OUT/README.md" <<EOF
# Java canonical build output

- Source SHA: \`$SOURCE_SHA\`
- Tool Java project SHA: \`$TOOL_SHA\`
- Moon task hash: \`$TASK_HASH\`

## Artifacts

- \`artifacts/template-java-project-0.1.0-SNAPSHOT.jar\`

## Evidence

- \`evidence/toolchain-build-provenance.txt\`
- \`evidence/tests/README.md\`
- canonical execution log: \`../../evidence/java-canonical/execution.log\`
EOF

exit "$STATUS"
