from pathlib import Path

from skillcheck.fixer import run_safe_remediation
from skillcheck.lint_rules import run_lint
from skillcheck.schema import load_policy


def test_safe_remediation_normalizes_frontmatter(tmp_path: Path) -> None:
    skill_dir = tmp_path / "good-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: BAD Skill !!!
description: "Demo"
unknown_field: true
---

# Body
""",
        encoding="utf-8",
    )

    policy = load_policy(policy_pack="balanced", expected_version=2)
    lint_before = run_lint(skill_dir, policy)

    result = run_safe_remediation(skill_dir, lint_before, policy, apply=True)

    assert result.changed
    assert "SKILL.md" in result.changed_files

    lint_after = run_lint(skill_dir, policy)
    codes = {issue.code for issue in lint_after.issues}
    assert "FRONTMATTER_UNKNOWN_FIELD" not in codes
    assert "FRONTMATTER_NAME_MISMATCH" not in codes
    assert "FRONTMATTER_NAME" not in codes


def test_safe_remediation_generates_missing_skill_md(tmp_path: Path) -> None:
    skill_dir = tmp_path / "new-skill"
    skill_dir.mkdir()

    policy = load_policy(policy_pack="balanced", expected_version=2)
    lint_before = run_lint(skill_dir, policy)
    assert any(issue.code == "SCHEMA_MISSING" for issue in lint_before.issues)

    result = run_safe_remediation(skill_dir, lint_before, policy, apply=True)

    assert result.changed
    assert (skill_dir / "SKILL.md").exists()

    lint_after = run_lint(skill_dir, policy)
    assert not any(issue.code == "SCHEMA_MISSING" for issue in lint_after.issues)


def test_safe_remediation_dry_run_does_not_write(tmp_path: Path) -> None:
    skill_dir = tmp_path / "dry-run-skill"
    skill_dir.mkdir()

    policy = load_policy(policy_pack="balanced", expected_version=2)
    lint_before = run_lint(skill_dir, policy)
    result = run_safe_remediation(skill_dir, lint_before, policy, apply=False)

    assert result.proposed
    assert not result.changed
    assert not (skill_dir / "SKILL.md").exists()
