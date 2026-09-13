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


artifact = Path("out/product/artifact.txt")
if not artifact.is_file():
    raise SystemExit("required product artifact is unavailable")

release_file = Path("release/metadata.txt")
artifact_digest = sha256(artifact.read_bytes())
release_digest = sha256(release_file.read_bytes())
count = increment_counter(Path(".executions/publication.count"))

output_root = Path("out/publication")
evidence_root = output_root / "evidence"
evidence_root.mkdir(parents=True, exist_ok=True)

package = output_root / "package.txt"
package.write_text(
    "publication package\n"
    f"product_artifact_digest={artifact_digest}\n"
    f"release_digest={release_digest}\n",
    encoding="utf-8",
)
package_digest = sha256(package.read_bytes())

execution = {
    "schema": "repo-build-tools.execution",
    "schema_version": 1,
    "capability": "publication",
    "owner": "fixture-domain",
    "action": "publish",
    "execution_count": count,
    "product_artifact_digest": artifact_digest,
    "release_digest": release_digest,
    "package_digest": package_digest,
    "status": "success",
}
(evidence_root / "execution.json").write_text(
    json.dumps(execution, indent=2) + "\n",
    encoding="utf-8",
)
(evidence_root / "execution.log").write_text(
    "publication\n"
    f"execution_count={count}\n"
    f"product_artifact_digest={artifact_digest}\n"
    f"release_digest={release_digest}\n"
    f"package_digest={package_digest}\n"
    "status=success\n",
    encoding="utf-8",
)

print(f"publication executed count={count} package={package_digest[:12]}")
