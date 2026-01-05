"""Static lint rules for SKILLCHECK."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .dependencies import collect_dependencies, DependencyIssue
from .schema import Policy, parse_skill_metadata, load_policy

SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[^\s]+")
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\\\")
REFERENCE_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
REFERENCE_INLINE_PATTERN = re.compile(r"\b(?:scripts|references|assets)/[A-Za-z0-9_./-]+")
IGNORE_DIRS = {".git", ".skillcheck", "__pycache__", "node_modules"}


@dataclass
class LintIssue:
    """Single lint finding."""

    code: str
    message: str
    path: str
    severity: str = "error"

    def to_dict(self) -> Dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "severity": self.severity,
        }

    @property
    def is_error(self) -> bool:
        return self.severity.lower() == "error"


@dataclass
class LintReport:
    """Aggregate lint findings for a Skill."""

    skill_name: str
    skill_version: Optional[str]
    issues: List[LintIssue]
    files_scanned: int

    @property
    def violations_count(self) -> int:
        return sum(1 for issue in self.issues if issue.is_error)

    @property
    def ok(self) -> bool:
        return self.violations_count == 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "skill": {
                "name": self.skill_name,
                "version": self.skill_version,
            },
            "summary": {
                "files_scanned": self.files_scanned,
                "issue_count": len(self.issues),
                "violations_count": self.violations_count,
            },
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _iter_files(skill_path: Path) -> Iterable[Path]:
    for candidate in sorted(skill_path.rglob("*")):
        if any(part in IGNORE_DIRS for part in candidate.parts):
            continue
        if candidate.is_file():
            yield candidate


def _issue_waived(policy: Policy, code: str, path: Path) -> bool:
    relative = str(path)
    for waiver in policy.waivers:
        waiver_path = waiver.get("path")
        waiver_code = waiver.get("rule")
        if waiver_path and waiver_code:
            if waiver_path == relative and waiver_code == code:
                return True
    return False


def _check_monolithic_skill(body: str, skill_md_path: Path, policy: Policy, issues: List[LintIssue]) -> None:
    max_lines = policy.skill_body_max_lines
    if max_lines <= 0:
        return
    line_count = len(body.splitlines())
    if line_count > max_lines:
        issues.append(
            LintIssue(
                code="SKILL_MONOLITH",
                path=str(skill_md_path),
                severity="warning",
                message=(
                    "SKILL.md body exceeds recommended size "
                    f"({line_count} lines > {max_lines}). Consider progressive disclosure via separate files."
                ),
            )
        )


def _check_forbidden_patterns(policy: Policy, path: Path, text: str, issues: List[LintIssue]) -> None:
    for rule in policy.forbidden_patterns:
        if rule.pattern.search(text):
            if _issue_waived(policy, rule.code, path):
                continue
            issues.append(
                LintIssue(
                    code=rule.code,
                    path=str(path),
                    message=rule.reason,
                )
            )


def _check_secret_pattern(path: Path, text: str, issues: List[LintIssue]) -> None:
    if SECRET_PATTERN.search(text):
        issues.append(
            LintIssue(
                code="SECRET_SUSPECT",
                path=str(path),
                message="Potential secret token detected",
            )
        )


def _check_path_traversal(path: Path, text: str, issues: List[LintIssue]) -> None:
    if PATH_TRAVERSAL_PATTERN.search(text):
        issues.append(
            LintIssue(
                code="PATH_TRAVERSAL",
                path=str(path),
                message="Relative path traversal detected ('../'); writes must stay within allowed globs.",
            )
        )


def _extract_references(body: str) -> List[str]:
    refs = set()
    for match in REFERENCE_LINK_PATTERN.finditer(body):
        path = match.group(1).strip()
        if not path or "://" in path or path.startswith("#"):
            continue
        refs.add(path.strip().strip("`").strip("\"'"))
    for match in REFERENCE_INLINE_PATTERN.finditer(body):
        refs.add(match.group(0))
    return sorted(refs)


def _check_file_references(body: str, skill_path: Path, skill_md_path: Path, issues: List[LintIssue]) -> None:
    for ref in _extract_references(body):
        if not ref:
            continue
        path = Path(ref)
        if path.is_absolute():
            issues.append(
                LintIssue(
                    code="REFERENCE_ABSOLUTE",
                    path=str(skill_md_path),
                    message=f"Absolute path references are not allowed: {ref}",
                )
            )
            continue
        if ".." in path.parts:
            issues.append(
                LintIssue(
                    code="REFERENCE_TRAVERSAL",
                    path=str(skill_md_path),
                    message=f"Reference escapes skill root: {ref}",
                )
            )
            continue
        if len(path.parts) > 2:
            issues.append(
                LintIssue(
                    code="REFERENCE_NESTED",
                    path=str(skill_md_path),
                    severity="warning",
                    message=f"Reference is more than one level deep: {ref}",
                )
            )
        if not (skill_path / path).exists():
            issues.append(
                LintIssue(
                    code="REFERENCE_MISSING",
                    path=str(skill_md_path),
                    severity="warning",
                    message=f"Referenced file not found: {ref}",
                )
            )


def _dependency_issue_to_lint(issue: DependencyIssue) -> LintIssue:
    return LintIssue(code=issue.code, message=issue.message, path=issue.path)


def _check_dependencies(skill_path: Path, policy: Policy, issues: List[LintIssue]) -> None:
    dependencies, dep_issues = collect_dependencies(skill_path)
    for issue in dep_issues:
        issues.append(_dependency_issue_to_lint(issue))
    for dep in dependencies:
        if not policy.is_dependency_allowed(dep.ecosystem, dep.name, dep.spec):
            issues.append(
                LintIssue(
                    code=f"DEPENDENCY_{dep.ecosystem.upper()}",
                    path=dep.source,
                    message=f"Dependency '{dep.spec}' is not in allowlist",
                )
            )


def _add_schema_issues(
    issues: List[LintIssue],
    schema_issues: Sequence,
    skill_md_path: Optional[Path],
    skill_path: Path,
) -> None:
    fallback = skill_md_path or (skill_path / "SKILL.md")
    for issue in schema_issues:
        path = issue.path or str(fallback)
        issues.append(
            LintIssue(
                code=issue.code,
                path=path,
                message=issue.message,
                severity=issue.severity,
            )
        )


def run_lint(skill_path: Path, policy: Optional[Policy] = None) -> LintReport:
    """Run lint rules for a Skill directory."""
    policy_obj = policy or load_policy()
    parse_result = parse_skill_metadata(skill_path, policy_obj)
    metadata = parse_result.metadata
    issues: List[LintIssue] = []

    _add_schema_issues(issues, parse_result.issues, parse_result.skill_md_path, skill_path)

    files = list(_iter_files(skill_path))
    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Binary files are skipped but counted.
            continue
        rel_path = file_path.relative_to(skill_path)
        _check_forbidden_patterns(policy_obj, rel_path, text, issues)
        _check_secret_pattern(rel_path, text, issues)
        _check_path_traversal(rel_path, text, issues)

    if parse_result.body:
        _check_monolithic_skill(
            parse_result.body,
            parse_result.skill_md_path or (skill_path / "SKILL.md"),
            policy_obj,
            issues,
        )
        _check_file_references(
            parse_result.body,
            skill_path,
            parse_result.skill_md_path or (skill_path / "SKILL.md"),
            issues,
        )

    _check_dependencies(skill_path, policy_obj, issues)

    skill_name = metadata.name or skill_path.name
    return LintReport(
        skill_name=skill_name,
        skill_version=metadata.version,
        issues=issues,
        files_scanned=len(files),
    )
