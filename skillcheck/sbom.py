"""Generate SPDX-lite SBOM for a Skill bundle."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_sbom(skill_path: Path, output_path: Path) -> Path:
    """Generate a minimal SPDX-style SBOM for the Skill directory."""
    files: List[Dict[str, str]] = []
    for file_path in sorted(skill_path.rglob("*")):
        if file_path.is_file():
            relative = str(file_path.relative_to(skill_path))
            files.append(
                {
                    "spdxid": f"SPDXRef-{relative.replace('/', '-')}",
                    "fileName": relative,
                    "checksums": [
                        {"algorithm": "SHA256", "checksumValue": _hash_file(file_path)}
                    ],
                }
            )
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "name": skill_path.name,
        "creationInfo": {
            "created": datetime.now(timezone.utc).isoformat(),
            "creators": ["Tool: skillcheck/0.1.0"],
        },
        "files": files,
    }
    output_path.write_text(json.dumps(sbom, indent=2), encoding="utf-8")
    return output_path
