"""Schema validation for SKILL.md and policy loader."""

from __future__ import annotations

import fnmatch
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

SKILL_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "allowed-tools",
    "metadata",
}
POLICY_PACKS = {"strict", "balanced", "research", "enterprise"}


class SkillValidationError(RuntimeError):
    """Raised when SKILL.md fails schema validation."""


@dataclass
class SchemaIssue:
    """Single schema validation issue."""

    code: str
    message: str
    severity: str = "error"
    path: str = ""


@dataclass
class SkillMetadata:
    """Parsed SKILL.md frontmatter (Agent Skills spec)."""

    name: str = ""
    description: str = ""
    license: Optional[str] = None
    compatibility: Optional[str] = None
    allowed_tools: List[str] = field(default_factory=list)
    allowed_tools_raw: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def version(self) -> Optional[str]:
        return self.metadata.get("version")


@dataclass
class PatternRule:
    """Compiled forbidden pattern from policy."""

    code: str
    pattern: Any
    reason: str


@dataclass
class Policy:
    """Policy document parsed from YAML."""

    raw: Dict[str, Any]
    path: str
    sha256: str
    pack: Optional[str] = None
    version: Optional[int] = None
    skill_name_max: int = 64
    skill_description_max: int = 1024
    skill_compatibility_max: int = 500
    skill_body_max_lines: int = 500
    allow_network_hosts: List[str] = field(default_factory=list)
    read_globs: List[str] = field(default_factory=list)
    write_globs: List[str] = field(default_factory=list)
    forbidden_patterns: List[PatternRule] = field(default_factory=list)
    waivers: List[Dict[str, str]] = field(default_factory=list)
    dependency_allowlists: Dict[str, List[str]] = field(default_factory=dict)
    allow_unknown_fields: bool = False
    legacy_fields: List[str] = field(default_factory=list)
    allow_tools: List[str] = field(default_factory=list)

    def is_read_allowed(self, relative_path: str) -> bool:
        if not self.read_globs:
            return True
        return any(fnmatch.fnmatch(relative_path, glob) for glob in self.read_globs)

    def is_write_allowed(self, relative_path: str) -> bool:
        if not self.write_globs:
            return False
        return any(fnmatch.fnmatch(relative_path, glob) for glob in self.write_globs)

    def is_dependency_allowed(self, ecosystem: str, name: str, spec: str) -> bool:
        allowlist = self.dependency_allowlists.get(f"allow_{ecosystem}", []) or []
        if not allowlist:
            return False
        return any(
            fnmatch.fnmatch(spec, pattern) or fnmatch.fnmatch(name, pattern)
            for pattern in allowlist
        )


def load_policy(
    policy_path: Optional[Path] = None,
    *,
    policy_pack: Optional[str] = None,
    expected_version: Optional[int] = None,
) -> Policy:
    """Load policy from YAML file (defaults to bundled policy)."""
    if policy_path is not None and policy_pack is not None:
        raise SkillValidationError("Choose either --policy or --policy-pack, not both")
    if policy_path is not None:
        raw_text = policy_path.read_text(encoding="utf-8")
        policy_location = str(policy_path.resolve())
        selected_pack = None
    elif policy_pack is not None:
        selected_pack = policy_pack.strip().lower()
        if selected_pack not in POLICY_PACKS:
            options = ", ".join(sorted(POLICY_PACKS))
            raise SkillValidationError(f"Unknown policy pack '{policy_pack}'. Choose one of: {options}")
        from importlib import resources

        resource = resources.files("skillcheck.policies").joinpath(f"{selected_pack}.policy.yaml")
        raw_text = resource.read_text(encoding="utf-8")
        policy_location = f"package://skillcheck/policies/{selected_pack}.policy.yaml"
    else:
        selected_pack = "balanced"
        from importlib import resources

        resource = resources.files("skillcheck.policies").joinpath("default.policy.yaml")
        raw_text = resource.read_text(encoding="utf-8")
        policy_location = "package://skillcheck/policies/default.policy.yaml"
    raw_policy = yaml.safe_load(raw_text) or {}
    raw_version = raw_policy.get("version")
    if expected_version is not None and int(raw_version or 0) != int(expected_version):
        raise SkillValidationError(
            f"Policy version mismatch: expected {expected_version}, got {raw_version}"
        )
    checksum = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    limits = raw_policy.get("limits", {}) if isinstance(raw_policy.get("limits", {}), dict) else {}
    patterns = raw_policy.get("forbidden_patterns", []) or []
    rules: List[PatternRule] = []
    for idx, entry in enumerate(patterns):
        pattern_str = entry.get("pattern")
        reason = entry.get("reason", "Policy violation")
        if not pattern_str:
            continue
        code = f"forbidden_pattern_{idx+1}"
        compiled = re.compile(pattern_str)
        rules.append(PatternRule(code=code, pattern=compiled, reason=reason))
    dependency_allowlists = raw_policy.get("dependencies", {}) or {}
    waivers = raw_policy.get("waivers", []) or []
    allow = raw_policy.get("allow", {}) if isinstance(raw_policy.get("allow", {}), dict) else {}
    read_globs = list(allow.get("filesystem", {}).get("read_globs", []) or [])
    write_globs = list(allow.get("filesystem", {}).get("write_globs", []) or [])
    frontmatter = raw_policy.get("frontmatter", {}) if isinstance(raw_policy.get("frontmatter", {}), dict) else {}
    allow_tools = list(allow.get("tools", {}).get("allowlist", []) or [])
    policy = Policy(
        raw=raw_policy,
        path=policy_location,
        sha256=checksum,
        pack=selected_pack or str(raw_policy.get("pack") or ""),
        version=int(raw_version) if isinstance(raw_version, int) else None,
        skill_name_max=int(limits.get("skill_name_max", 64)),
        skill_description_max=int(limits.get("skill_description_max", 1024)),
        skill_compatibility_max=int(limits.get("skill_compatibility_max", 500)),
        skill_body_max_lines=int(limits.get("skill_body_max_lines", 500)),
        allow_network_hosts=list(allow.get("network", {}).get("hosts", []) or []),
        read_globs=read_globs,
        write_globs=write_globs,
        forbidden_patterns=rules,
        waivers=waivers,
        dependency_allowlists=dependency_allowlists,
        allow_unknown_fields=bool(frontmatter.get("allow_unknown_fields", False)),
        legacy_fields=list(frontmatter.get("legacy_fields", []) or []),
        allow_tools=allow_tools,
    )
    return policy


def find_skill_md(skill_path: Path) -> Optional[Path]:
    """Locate SKILL.md (or skill.md) in a skill directory."""
    for name in ("SKILL.md", "skill.md"):
        candidate = skill_path / name
        if candidate.exists():
            return candidate
    return None


def _extract_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    if not text.startswith("---"):
        raise SkillValidationError("SKILL.md must begin with YAML front matter delimited by ---")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillValidationError("SKILL.md front matter is not properly closed with ---")
    frontmatter_str = parts[1]
    markdown_body = parts[2].strip()
    try:
        parsed = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise SkillValidationError(f"Invalid YAML front matter: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SkillValidationError("SKILL.md front matter must be a YAML mapping")
    return parsed, markdown_body


def _normalize_name(value: str) -> str:
    return unicodedata.normalize("NFKC", value.strip())


def _normalize_metadata(raw_meta: Any) -> Tuple[Dict[str, str], Optional[str]]:
    if raw_meta is None:
        return {}, None
    if not isinstance(raw_meta, dict):
        return {}, "Field 'metadata' must be a mapping"
    normalized = {str(key): str(val) for key, val in raw_meta.items()}
    return normalized, None


def _extract_allowed_tools(raw_value: Any) -> Tuple[List[str], Optional[str], Optional[str]]:
    if raw_value is None:
        return [], None, None
    if not isinstance(raw_value, str):
        return [], None, "Field 'allowed-tools' must be a space-delimited string"
    stripped = raw_value.strip()
    if not stripped:
        return [], raw_value, "Field 'allowed-tools' must not be empty when provided"
    tokens = stripped.split()
    return tokens, raw_value, None


def validate_frontmatter(frontmatter: Dict[str, Any], skill_path: Path, policy: Policy) -> List[SchemaIssue]:
    """Validate frontmatter against the Agent Skills spec and policy."""
    issues: List[SchemaIssue] = []

    extra_fields = set(frontmatter.keys()) - SKILL_FRONTMATTER_FIELDS
    legacy_fields = {field for field in extra_fields if field in set(policy.legacy_fields)}
    unknown_fields = extra_fields - legacy_fields
    if legacy_fields:
        issues.append(
            SchemaIssue(
                code="FRONTMATTER_LEGACY_FIELD",
                message=f"Legacy frontmatter fields present: {', '.join(sorted(legacy_fields))}",
                severity="warning",
            )
        )
    if unknown_fields:
        severity = "warning" if policy.allow_unknown_fields else "error"
        issues.append(
            SchemaIssue(
                code="FRONTMATTER_UNKNOWN_FIELD",
                message=f"Unexpected frontmatter fields: {', '.join(sorted(unknown_fields))}",
                severity=severity,
            )
        )

    raw_name = frontmatter.get("name")
    if not isinstance(raw_name, str) or not raw_name.strip():
        issues.append(
            SchemaIssue(
                code="FRONTMATTER_NAME",
                message="Field 'name' must be a non-empty string",
            )
        )
    else:
        normalized = _normalize_name(raw_name)
        if len(normalized) > policy.skill_name_max:
            issues.append(
                SchemaIssue(
                    code="FRONTMATTER_NAME",
                    message=(
                        f"Skill name exceeds maximum length ({len(normalized)} > {policy.skill_name_max})"
                    ),
                )
            )
        if normalized != normalized.lower():
            issues.append(
                SchemaIssue(
                    code="FRONTMATTER_NAME",
                    message=f"Skill name '{normalized}' must be lowercase",
                )
            )
        if normalized.startswith("-") or normalized.endswith("-"):
            issues.append(
                SchemaIssue(
                    code="FRONTMATTER_NAME",
                    message="Skill name cannot start or end with a hyphen",
                )
            )
        if "--" in normalized:
            issues.append(
                SchemaIssue(
                    code="FRONTMATTER_NAME",
                    message="Skill name cannot contain consecutive hyphens",
                )
            )
        if not all(char.isalnum() or char == "-" for char in normalized):
            issues.append(
                SchemaIssue(
                    code="FRONTMATTER_NAME",
                    message=(
                        f"Skill name '{normalized}' contains invalid characters; "
                        "only letters, digits, and hyphens are allowed"
                    ),
                )
            )
        if skill_path:
            dir_name = _normalize_name(skill_path.name)
            if dir_name != normalized:
                issues.append(
                    SchemaIssue(
                        code="FRONTMATTER_NAME_MISMATCH",
                        message=(
                            f"Directory name '{skill_path.name}' must match skill name '{normalized}'"
                        ),
                    )
                )

    raw_description = frontmatter.get("description")
    if not isinstance(raw_description, str) or not raw_description.strip():
        issues.append(
            SchemaIssue(
                code="FRONTMATTER_DESCRIPTION",
                message="Field 'description' must be a non-empty string",
            )
        )
    else:
        description = raw_description.strip()
        if len(description) > policy.skill_description_max:
            issues.append(
                SchemaIssue(
                    code="FRONTMATTER_DESCRIPTION",
                    message=(
                        "Skill description exceeds maximum length "
                        f"({len(description)} > {policy.skill_description_max})"
                    ),
                )
            )

    raw_license = frontmatter.get("license")
    if raw_license is not None and not isinstance(raw_license, str):
        issues.append(
            SchemaIssue(
                code="FRONTMATTER_LICENSE",
                message="Field 'license' must be a string when provided",
            )
        )

    raw_compat = frontmatter.get("compatibility")
    if raw_compat is not None:
        if not isinstance(raw_compat, str):
            issues.append(
                SchemaIssue(
                    code="FRONTMATTER_COMPATIBILITY",
                    message="Field 'compatibility' must be a string when provided",
                )
            )
        elif len(raw_compat) > policy.skill_compatibility_max:
            issues.append(
                SchemaIssue(
                    code="FRONTMATTER_COMPATIBILITY",
                    message=(
                        "Compatibility exceeds maximum length "
                        f"({len(raw_compat)} > {policy.skill_compatibility_max})"
                    ),
                )
            )

    _, allowed_raw, allowed_issue = _extract_allowed_tools(frontmatter.get("allowed-tools"))
    if allowed_issue:
        issues.append(
            SchemaIssue(
                code="FRONTMATTER_ALLOWED_TOOLS",
                message=allowed_issue,
            )
        )
    elif allowed_raw:
        tools = allowed_raw.split()
        if policy.allow_tools:
            for token in tools:
                base = token.split("(", 1)[0]
                if not any(
                    fnmatch.fnmatch(token, pattern) or fnmatch.fnmatch(base, pattern)
                    for pattern in policy.allow_tools
                ):
                    issues.append(
                        SchemaIssue(
                            code="FRONTMATTER_ALLOWED_TOOLS",
                            message=f"Allowed tool '{token}' is not permitted by policy",
                        )
                    )

    _, meta_issue = _normalize_metadata(frontmatter.get("metadata"))
    if meta_issue:
        issues.append(
            SchemaIssue(
                code="FRONTMATTER_METADATA",
                message=meta_issue,
            )
        )

    return issues


@dataclass
class SkillParseResult:
    metadata: SkillMetadata
    body: str
    issues: List[SchemaIssue]
    skill_md_path: Optional[Path] = None


def parse_skill_metadata(skill_path: Path, policy: Optional[Policy] = None) -> SkillParseResult:
    """Parse SKILL.md frontmatter/body and collect schema issues."""
    policy_obj = policy or load_policy()
    issues: List[SchemaIssue] = []
    skill_md = find_skill_md(skill_path)
    if not skill_md:
        issues.append(
            SchemaIssue(
                code="SCHEMA_MISSING",
                message="Missing required file: SKILL.md (or skill.md)",
            )
        )
        return SkillParseResult(metadata=SkillMetadata(raw={}), body="", issues=issues, skill_md_path=None)

    try:
        text = skill_md.read_text(encoding="utf-8")
        frontmatter, body = _extract_frontmatter(text)
    except SkillValidationError as exc:
        issues.append(
            SchemaIssue(
                code="SCHEMA_INVALID",
                message=str(exc),
            )
        )
        return SkillParseResult(metadata=SkillMetadata(raw={}), body="", issues=issues, skill_md_path=skill_md)

    metadata_map, _ = _normalize_metadata(frontmatter.get("metadata"))
    allowed_tools, allowed_tools_raw, _ = _extract_allowed_tools(frontmatter.get("allowed-tools"))
    raw_name = frontmatter.get("name")
    raw_description = frontmatter.get("description")
    metadata = SkillMetadata(
        name=_normalize_name(raw_name) if isinstance(raw_name, str) else "",
        description=raw_description.strip() if isinstance(raw_description, str) else "",
        license=frontmatter.get("license") if isinstance(frontmatter.get("license"), str) else None,
        compatibility=frontmatter.get("compatibility") if isinstance(frontmatter.get("compatibility"), str) else None,
        allowed_tools=allowed_tools,
        allowed_tools_raw=allowed_tools_raw,
        metadata=metadata_map,
        raw=frontmatter,
    )
    issues.extend(validate_frontmatter(frontmatter, skill_path, policy_obj))
    return SkillParseResult(metadata=metadata, body=body, issues=issues, skill_md_path=skill_md)


def load_skill_metadata(skill_path: Path, policy: Optional[Policy] = None) -> Tuple[SkillMetadata, str]:
    """Load SKILL.md metadata and body, validating against policy limits."""
    result = parse_skill_metadata(skill_path, policy)
    errors = [issue for issue in result.issues if issue.severity == "error"]
    if errors:
        joined = "; ".join(issue.message for issue in errors)
        raise SkillValidationError(joined)
    return result.metadata, result.body


def policy_summary(policy: Policy) -> Dict[str, Any]:
    """Return a stable summary for attestation payloads."""
    probe_cfg = policy.raw.get("probe", {})
    if not isinstance(probe_cfg, dict):
        probe_cfg = {}
    return {
        "path": policy.path,
        "sha256": policy.sha256,
        "pack": policy.pack,
        "version": policy.version if policy.version is not None else policy.raw.get("version"),
        "limits": {
            "skill_name_max": policy.skill_name_max,
            "skill_description_max": policy.skill_description_max,
            "skill_compatibility_max": policy.skill_compatibility_max,
            "skill_body_max_lines": policy.skill_body_max_lines,
        },
        "frontmatter": {
            "allow_unknown_fields": policy.allow_unknown_fields,
            "legacy_fields": policy.legacy_fields,
        },
        "allow": {
            "network_hosts": policy.allow_network_hosts,
            "filesystem_read": policy.read_globs,
            "filesystem_write": policy.write_globs,
            "tools": policy.allow_tools,
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
