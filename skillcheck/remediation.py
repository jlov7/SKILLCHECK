"""Guided remediation mappings for common finding codes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RemediationGuide:
    code_pattern: str
    title: str
    why: str
    fixes: List[str]


REMEDIATION_GUIDES: List[RemediationGuide] = [
    RemediationGuide(
        code_pattern="EGRESS_",
        title="Outbound network egress detected",
        why="The skill tries to contact external services that are not allowlisted.",
        fixes=[
            "Remove network calls from scripts/resources unless required.",
            "If required, add explicit hosts under allow.network.hosts in the selected policy.",
            "Re-run `skillcheck probe --exec` to verify sandbox egress is blocked or allowlisted.",
        ],
    ),
    RemediationGuide(
        code_pattern="WRITE_",
        title="Disallowed filesystem write detected",
        why="The skill attempts writes outside approved scratch paths.",
        fixes=[
            "Limit writes to `scratch/**` (or approved write globs) and avoid absolute paths.",
            "Update allow.filesystem.write_globs only for minimal required paths.",
            "Re-run probe to confirm no disallowed write findings remain.",
        ],
    ),
    RemediationGuide(
        code_pattern="SECRET_SUSPECT",
        title="Potential secret detected",
        why="Credential-like text was found in skill content.",
        fixes=[
            "Remove hard-coded tokens/keys from all files.",
            "Use runtime secret injection mechanisms outside the skill bundle.",
            "Rotate any leaked secrets before shipping.",
        ],
    ),
    RemediationGuide(
        code_pattern="DEPENDENCY_",
        title="Dependency outside policy allowlist",
        why="Dependency declarations include packages not approved by policy.",
        fixes=[
            "Remove unnecessary packages from requirements/pyproject/package.json.",
            "Add explicit allowlist entries for required packages in policy.dependencies.",
            "Pin versions for approved packages to reduce supply-chain drift.",
        ],
    ),
    RemediationGuide(
        code_pattern="FRONTMATTER_",
        title="Frontmatter schema mismatch",
        why="SKILL.md metadata does not match the Agent Skills schema or policy limits.",
        fixes=[
            "Ensure name/description fields are valid and within policy limits.",
            "Remove unknown frontmatter fields unless policy allows them.",
            "Fix allowed-tools formatting and values to match policy allowlist.",
        ],
    ),
    RemediationGuide(
        code_pattern="SCHEMA_",
        title="SKILL.md schema file issue",
        why="The required SKILL.md file is missing or malformed.",
        fixes=[
            "Ensure SKILL.md (or skill.md) exists at the skill root.",
            "Start with valid YAML frontmatter delimited by `---`.",
            "Validate required metadata keys (`name`, `description`) are present.",
        ],
    ),
    RemediationGuide(
        code_pattern="REFERENCE_",
        title="Broken or unsafe file reference",
        why="SKILL.md references files that are missing, absolute, or escaping skill root.",
        fixes=[
            "Use relative paths within the skill directory only.",
            "Create missing referenced files or remove stale references.",
            "Avoid deep nesting for referenced files when possible.",
        ],
    ),
    RemediationGuide(
        code_pattern="PATH_TRAVERSAL",
        title="Path traversal pattern detected",
        why="The bundle contains `../` style traversal patterns that may escape the skill root.",
        fixes=[
            "Replace traversal paths with safe relative paths under the skill root.",
            "Constrain writes to policy-approved write globs.",
            "Re-run lint/probe to verify traversal findings are cleared.",
        ],
    ),
]


def get_remediation(code: str) -> Optional[RemediationGuide]:
    """Return the best remediation guide for a finding code."""
    normalized = code.strip().upper()
    if not normalized:
        return None
    exact_map: Dict[str, RemediationGuide] = {
        guide.code_pattern: guide
        for guide in REMEDIATION_GUIDES
        if not guide.code_pattern.endswith("_")
    }
    if normalized in exact_map:
        return exact_map[normalized]
    for guide in REMEDIATION_GUIDES:
        if guide.code_pattern.endswith("_") and normalized.startswith(guide.code_pattern):
            return guide
    return None
