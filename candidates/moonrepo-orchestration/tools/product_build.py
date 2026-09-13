#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def increment_counter(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    value = int(path.read_text(encoding="utf-8")) + 1 if path.exists() else 1
    path.write_text(f"{value}\n", encoding="utf-8")
    return value


source = Path("src/product/core.txt")
source_bytes = source.read_bytes()
source_digest = sha256(source_bytes)
count = increment_counter(Path(".executions/product.count"))

output_root = Path("out/product")
evidence_root = output_root / "evidence"
evidence_root.mkdir(parents=True, exist_ok=True)

artifact = output_root / "artifact.txt"
artifact.write_text(
    "product.build artifact\n"
    f"source_digest={source_digest}\n",
    encoding="utf-8",
)
artifact_digest = sha256(artifact.read_bytes())

execution = {
    "schema": "repo-build-tools.execution",
    "schema_version": 1,
    "capability": "product.build",
    "owner": "fixture-domain",
    "action": "build",
    "execution_count": count,
    "source_digest": source_digest,
    "artifact_digest": artifact_digest,
    "status": "success",
}
(evidence_root / "execution.json").write_text(
    json.dumps(execution, indent=2) + "\n",
    encoding="utf-8",
)
(evidence_root / "execution.log").write_text(
    "product.build\n"
    f"execution_count={count}\n"
    f"source_digest={source_digest}\n"
    f"artifact_digest={artifact_digest}\n"
    "status=success\n",
    encoding="utf-8",
)

print(f"product.build executed count={count} source={source_digest[:12]} artifact={artifact_digest[:12]}")
