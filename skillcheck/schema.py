"""Schema validation for SKILL.md and policy loader."""

from __future__ import annotations

import fnmatch
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, ValidationError, field_validator

try:
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(?P<frontmatter>.+?)\n---\s*\n", re.DOTALL)


class SkillValidationError(RuntimeError):
    """Raised when SKILL.md fails schema validation."""


class SkillMetadata(BaseModel):
    """Pydantic model describing SKILL.md front matter."""

    name: str
    description: str
    version: Optional[str] = None

    @field_validator("name")
    def name_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Skill name must not be empty")
        return value

    @field_validator("description")
    def description_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Skill description must not be empty")
        return value


@dataclass
class PatternRule:
    """Compiled forbidden pattern from policy."""

    code: str
    pattern: re.Pattern[str]
    reason: str


@dataclass
class Policy:
    """Policy document parsed from YAML."""

    raw: Dict[str, Any]
    path: str
    sha256: str
    skill_name_max: int = 64
    skill_description_max: int = 200
    allow_network_hosts: List[str] = field(default_factory=list)
    read_globs: List[str] = field(default_factory=list)
    write_globs: List[str] = field(default_factory=list)
    forbidden_patterns: List[PatternRule] = field(default_factory=list)
    waivers: List[Dict[str, str]] = field(default_factory=list)
    dependency_allowlists: Dict[str, List[str]] = field(default_factory=dict)

    def is_read_allowed(self, relative_path: str) -> bool:
        if not self.read_globs:
            return True
        return any(fnmatch.fnmatch(relative_path, glob) for glob in self.read_globs)

    def is_write_allowed(self, relative_path: str) -> bool:
        if not self.write_globs:
            return False
        return any(fnmatch.fnmatch(relative_path, glob) for glob in self.write_globs)


def load_policy(policy_path: Optional[Path] = None) -> Policy:
    """Load policy from YAML file (defaults to bundled policy)."""
    if policy_path is not None:
        raw_text = policy_path.read_text(encoding="utf-8")
        policy_location = str(policy_path.resolve())
    else:
        resource = resources.files("skillcheck.policies").joinpath("default.policy.yaml")
        raw_text = resource.read_text(encoding="utf-8")
        policy_location = "package://skillcheck/policies/default.policy.yaml"
    raw_policy = yaml.safe_load(raw_text) or {}
    checksum = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    limits = raw_policy.get("limits", {})
    patterns = raw_policy.get("forbidden_patterns", [])
    rules: List[PatternRule] = []
    for idx, entry in enumerate(patterns):
        pattern_str = entry.get("pattern")
        reason = entry.get("reason", "Policy violation")
        if not pattern_str:
            continue
        code = f"forbidden_pattern_{idx+1}"
        compiled = re.compile(pattern_str)
        rules.append(PatternRule(code=code, pattern=compiled, reason=reason))
    dependency_allowlists = raw_policy.get("dependencies", {})
    waivers = raw_policy.get("waivers", []) or []
    read_globs = list(raw_policy.get("allow", {}).get("filesystem", {}).get("read_globs", []) or [])
    write_globs = list(raw_policy.get("allow", {}).get("filesystem", {}).get("write_globs", []) or [])
    policy = Policy(
        raw=raw_policy,
        path=policy_location,
        sha256=checksum,
        skill_name_max=int(limits.get("skill_name_max", 64)),
        skill_description_max=int(limits.get("skill_description_max", 200)),
        allow_network_hosts=list(raw_policy.get("allow", {}).get("network", {}).get("hosts", []) or []),
        read_globs=read_globs,
        write_globs=write_globs,
        forbidden_patterns=rules,
        waivers=waivers,
        dependency_allowlists=dependency_allowlists,
    )
    return policy


def _extract_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        raise SkillValidationError("SKILL.md must begin with YAML front matter delimited by ---")
    frontmatter = match.group("frontmatter")
    markdown_body = text[match.end() :]
    try:
        parsed = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise SkillValidationError(f"Invalid YAML front matter: {exc}") from exc
    return parsed, markdown_body


def load_skill_metadata(skill_path: Path, policy: Optional[Policy] = None) -> Tuple[SkillMetadata, str]:
    """Load SKILL.md metadata and body, validating against policy limits."""
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise SkillValidationError(f"Missing SKILL.md in {skill_path}")
    text = skill_md.read_text(encoding="utf-8")
    frontmatter, body = _extract_frontmatter(text)
    try:
        metadata = SkillMetadata(**frontmatter)
    except ValidationError as exc:
        raise SkillValidationError(str(exc)) from exc
    policy_obj = policy or load_policy()
    if len(metadata.name) > policy_obj.skill_name_max:
        raise SkillValidationError(
            f"Skill name exceeds maximum length ({len(metadata.name)} > {policy_obj.skill_name_max})"
        )
    if len(metadata.description) > policy_obj.skill_description_max:
        raise SkillValidationError(
            f"Skill description exceeds maximum length ({len(metadata.description)} > {policy_obj.skill_description_max})"
        )
    return metadata, body


def policy_summary(policy: Policy) -> Dict[str, Any]:
    """Return a stable summary for attestation payloads."""
    probe_cfg = policy.raw.get("probe", {})
    if not isinstance(probe_cfg, dict):
        probe_cfg = {}
    return {
        "path": policy.path,
        "sha256": policy.sha256,
        "limits": {
            "skill_name_max": policy.skill_name_max,
            "skill_description_max": policy.skill_description_max,
        },
        "allow": {
            "network_hosts": policy.allow_network_hosts,
            "filesystem_read": policy.read_globs,
            "filesystem_write": policy.write_globs,
        },
        "forbidden_patterns": [
            {
                "code": rule.code,
                "pattern": rule.pattern.pattern,
                "reason": rule.reason,
            }
            for rule in policy.forbidden_patterns
        ],
        "waivers": policy.waivers,
        "dependencies": policy.dependency_allowlists,
        "probe": {
            "enable_exec": bool(probe_cfg.get("enable_exec", False)),
            "exec_globs": probe_cfg.get("exec_globs") or [],
            "timeout": probe_cfg.get("timeout", 5),
        },
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }
