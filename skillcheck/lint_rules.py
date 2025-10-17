"""Static lint rules for SKILLCHECK."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .schema import Policy, SkillValidationError, load_skill_metadata

SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[^\s]+")
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\\\")
MONOLITH_CHAR_THRESHOLD = 5000


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


def _check_monolithic_skill(body: str, skill_path: Path, issues: List[LintIssue]) -> None:
    if len(body) > MONOLITH_CHAR_THRESHOLD:
        issues.append(
            LintIssue(
                code="SKILL_MONOLITH",
                path=str(skill_path / "SKILL.md"),
                severity="warning",
                message=(
                    "SKILL.md body exceeds recommended size. Consider progressive disclosure via separate files."
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


def run_lint(skill_path: Path, policy: Optional[Policy] = None) -> LintReport:
    """Run lint rules for a Skill directory."""
    policy_obj = policy or load_policy()
    try:
        metadata, body = load_skill_metadata(skill_path, policy_obj)
    except SkillValidationError as exc:
        issue = LintIssue(
            code="SCHEMA_INVALID",
            path=str(skill_path / "SKILL.md"),
            message=str(exc),
        )
        return LintReport(
            skill_name=skill_path.name,
            skill_version=None,
            issues=[issue],
            files_scanned=0,
        )
    issues: List[LintIssue] = []
    files = list(_iter_files(skill_path))
    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Binary files are skipped but counted.
            continue
        _check_forbidden_patterns(policy_obj, file_path.relative_to(skill_path), text, issues)
        _check_secret_pattern(file_path.relative_to(skill_path), text, issues)
        _check_path_traversal(file_path.relative_to(skill_path), text, issues)
    _check_monolithic_skill(body, skill_path, issues)
    return LintReport(
        skill_name=metadata.name,
        skill_version=metadata.version,
        issues=issues,
        files_scanned=len(files),
    )
