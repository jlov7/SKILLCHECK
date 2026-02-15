"""Deterministic safe remediations for SKILLCHECK findings."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from .lint_rules import LintReport
from .schema import Policy, SKILL_FRONTMATTER_FIELDS, find_skill_md

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass
class FixAction:
    code: str
    message: str
    path: str


@dataclass
class FixResult:
    skill_name: str
    applied: List[FixAction] = field(default_factory=list)
    skipped: List[FixAction] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)

    @property
    def proposed(self) -> bool:
        return bool(self.applied or self.skipped)

    @property
    def changed(self) -> bool:
        return bool(self.changed_files)

    def to_dict(self) -> Dict[str, object]:
        return {
            "skill_name": self.skill_name,
            "applied": [action.__dict__ for action in self.applied],
            "skipped": [action.__dict__ for action in self.skipped],
            "errors": self.errors,
            "changed_files": self.changed_files,
            "changed": self.changed,
            "proposed": self.proposed,
        }


def _slugify_name(value: str) -> str:
    lowered = value.strip().lower().replace("_", "-").replace(" ", "-")
    cleaned = re.sub(r"[^a-z0-9-]+", "-", lowered)
    collapsed = re.sub(r"-+", "-", cleaned).strip("-")
    return collapsed or "skill"


def _parse_skill_md(text: str) -> Tuple[Dict[str, Any], str, bool]:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            raw_frontmatter = parts[1]
            body = parts[2].lstrip("\n")
            try:
                parsed = yaml.safe_load(raw_frontmatter) or {}
            except yaml.YAMLError:
                return {}, body, False
            if isinstance(parsed, dict):
                return parsed, body, True
    return {}, text.strip() + "\n", False


def _render_skill_md(frontmatter: Dict[str, Any], body: str) -> str:
    ordered: Dict[str, Any] = {}
    for key in ("name", "description", "license", "compatibility", "allowed-tools", "metadata"):
        if key in frontmatter:
            ordered[key] = frontmatter[key]
    for key, value in frontmatter.items():
        if key not in ordered:
            ordered[key] = value
    header = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=False).strip()
    cleaned_body = body.lstrip("\n")
    return f"---\n{header}\n---\n\n{cleaned_body.rstrip()}\n"


def _fix_frontmatter(frontmatter: Dict[str, Any], dir_name: str, policy: Policy) -> Tuple[Dict[str, Any], List[FixAction], bool]:
    fixes: List[FixAction] = []
    changed = False
    result = dict(frontmatter)

    directory_slug = _slugify_name(dir_name)

    name = result.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.match(name):
        result["name"] = directory_slug
        fixes.append(FixAction(code="FRONTMATTER_NAME", message="Normalized skill name to directory slug", path="SKILL.md"))
        changed = True
    elif name != directory_slug:
        result["name"] = directory_slug
        fixes.append(FixAction(code="FRONTMATTER_NAME_MISMATCH", message="Aligned frontmatter name to directory", path="SKILL.md"))
        changed = True

    description = result.get("description")
    if not isinstance(description, str) or not description.strip():
        result["description"] = f"Skill {directory_slug}"
        fixes.append(FixAction(code="FRONTMATTER_DESCRIPTION", message="Added missing description", path="SKILL.md"))
        changed = True
    else:
        trimmed = description.strip()
        if len(trimmed) > policy.skill_description_max:
            result["description"] = trimmed[: policy.skill_description_max].rstrip()
            fixes.append(FixAction(code="FRONTMATTER_DESCRIPTION", message="Trimmed description to policy limit", path="SKILL.md"))
            changed = True

    compatibility = result.get("compatibility")
    if isinstance(compatibility, str) and len(compatibility) > policy.skill_compatibility_max:
        result["compatibility"] = compatibility[: policy.skill_compatibility_max].rstrip()
        fixes.append(FixAction(code="FRONTMATTER_COMPATIBILITY", message="Trimmed compatibility to policy limit", path="SKILL.md"))
        changed = True

    allowed_tools = result.get("allowed-tools")
    if isinstance(allowed_tools, list):
        tokens = [str(token).strip() for token in allowed_tools if str(token).strip()]
        result["allowed-tools"] = " ".join(tokens)
        fixes.append(FixAction(code="FRONTMATTER_ALLOWED_TOOLS", message="Normalized allowed-tools list to string", path="SKILL.md"))
        changed = True

    metadata = result.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        result["metadata"] = {}
        fixes.append(FixAction(code="FRONTMATTER_METADATA", message="Reset invalid metadata to empty mapping", path="SKILL.md"))
        changed = True

    if not policy.allow_unknown_fields:
        unknown = [key for key in list(result.keys()) if key not in SKILL_FRONTMATTER_FIELDS]
        if unknown:
            for key in unknown:
                result.pop(key, None)
            fixes.append(FixAction(code="FRONTMATTER_UNKNOWN_FIELD", message=f"Removed unsupported fields: {', '.join(sorted(unknown))}", path="SKILL.md"))
            changed = True

    return result, fixes, changed


def run_safe_remediation(skill_path: Path, lint_report: LintReport, policy: Policy, *, apply: bool) -> FixResult:
    """Apply deterministic safe remediations for schema/frontmatter findings."""
    skill_name = lint_report.skill_name or skill_path.name
    result = FixResult(skill_name=skill_name)
    skill_md = find_skill_md(skill_path)

    if skill_md is None:
        template_name = _slugify_name(skill_path.name)
        action = FixAction(
            code="SCHEMA_MISSING",
            message="Generate minimal SKILL.md template",
            path="SKILL.md",
        )
        if apply:
            content = (
                f"---\n"
                f"name: {template_name}\n"
                f"description: \"Skill {template_name}\"\n"
                f"---\n\n"
                f"# {template_name}\n"
            )
            (skill_path / "SKILL.md").write_text(content, encoding="utf-8")
            result.applied.append(action)
            result.changed_files.append("SKILL.md")
        else:
            result.skipped.append(action)
        return result

    try:
        original_text = skill_md.read_text(encoding="utf-8")
    except OSError as exc:
        result.errors.append(f"Failed reading {skill_md}: {exc}")
        return result

    frontmatter, body, parsed = _parse_skill_md(original_text)
    if not parsed:
        frontmatter = {
            "name": _slugify_name(skill_path.name),
            "description": f"Skill {_slugify_name(skill_path.name)}",
        }
        result.skipped.append(
            FixAction(
                code="SCHEMA_INVALID",
                message="Frontmatter parsing failed; rebuilt minimal frontmatter",
                path=str(skill_md.name),
            )
        )

    fixed_frontmatter, fixes, changed = _fix_frontmatter(frontmatter, skill_path.name, policy)

    if not changed:
        return result

    for fix in fixes:
        if apply:
            result.applied.append(fix)
        else:
            result.skipped.append(fix)

    if not apply:
        return result

    new_text = _render_skill_md(fixed_frontmatter, body)
    if new_text != original_text:
        skill_md.write_text(new_text, encoding="utf-8")
        result.changed_files.append(skill_md.name)

    return result
