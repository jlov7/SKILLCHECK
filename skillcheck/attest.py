"""Attestation builder for SKILLCHECK."""

from __future__ import annotations

import hashlib
import json
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from .lint_rules import LintReport
from .probe import ProbeResult
from .schema import Policy, parse_skill_metadata, policy_summary
from .utils import slugify


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AttestationBuilder:
    """Create attestation manifest and optional signature."""

    def __init__(self, policy: Policy):
        self.policy = policy

    def _collect_file_hashes(self, skill_path: Path) -> Dict[str, str]:
        hashes: Dict[str, str] = {}
        for file_path in sorted(skill_path.rglob("*")):
            if file_path.is_file():
                hashes[str(file_path.relative_to(skill_path))] = _hash_file(file_path)
        return hashes

    def _sign_payload(self, payload: bytes) -> Dict[str, str]:
        if importlib.util.find_spec("sigstore") is None:
            return {
                "mode": "unsigned",
                "reason": "sigstore library not installed; attestation stored without signature",
            }
        try:
            from sigstore.sign import Signer  # type: ignore
            from sigstore.sign import SigningContext  # type: ignore
        except Exception:  # pragma: no cover - optional dependency fallback
            return {
                "mode": "unsigned",
                "reason": "sigstore keyless signing unavailable in this environment",
            }
        try:  # pragma: no cover - best effort signing
            context = SigningContext.staging()
            signer = Signer.production() if hasattr(Signer, "production") else Signer(context)
            result = signer.sign(payload)
            return {
                "mode": "sigstore",
                "signature": result.signature.decode("utf-8") if hasattr(result.signature, "decode") else str(result.signature),
                "certificate": getattr(result, "certificate", ""),
            }
        except Exception:
            return {
                "mode": "unsigned",
                "reason": "sigstore signing failed; recorded unsigned attestation",
            }

    def build(
        self,
        skill_path: Path,
        lint_report: LintReport,
        probe_result: ProbeResult,
        sbom_path: Path,
        output_dir: Path,
        *,
        artifact_stem: Optional[str] = None,
        source_path: Optional[str] = None,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = artifact_stem or slugify(lint_report.skill_name)
        parsed = parse_skill_metadata(skill_path, self.policy)
        skill_meta = parsed.metadata
        payload = {
            "schemaVersion": "1.0",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "skill": {
                "name": lint_report.skill_name,
                "version": lint_report.skill_version,
                "path": source_path or str(skill_path),
                "license": skill_meta.license,
                "compatibility": skill_meta.compatibility,
                "allowed_tools": skill_meta.allowed_tools,
                "metadata": skill_meta.metadata,
            },
            "spec": {
                "name": "Agent Skills",
                "url": "https://agentskills.io/specification",
            },
            "policy": policy_summary(self.policy),
            "lint": lint_report.to_dict(),
            "probe": probe_result.to_dict(),
            "sbom": {
                "path": str(sbom_path),
                "sha256": _hash_file(sbom_path),
            },
            "files": self._collect_file_hashes(skill_path),
        }
        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload["signature"] = self._sign_payload(serialized)
        attestation_path = output_dir / f"{stem}.attestation.json"
        attestation_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return attestation_path
