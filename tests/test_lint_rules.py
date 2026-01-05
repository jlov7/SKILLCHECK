from pathlib import Path

from skillcheck.bundle import open_skill_bundle
from skillcheck.lint_rules import run_lint
from skillcheck.schema import load_policy


def _make_skill(tmp_path: Path, body: str) -> Path:
    skill_dir = tmp_path / "secret-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: secret-skill
description: "Demo skill for lint testing."
---

{body}
""",
        encoding="utf-8",
    )
    (skill_dir / "config.txt").write_text("API_KEY = super-secret-token", encoding="utf-8")
    return skill_dir


def test_lint_detects_secret(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, "# Body")
    report = run_lint(skill_dir, load_policy())
    assert any(issue.code == "SECRET_SUSPECT" for issue in report.issues)


def test_lint_flags_forbidden_patterns() -> None:
    project_root = Path(__file__).resolve().parents[1]
    skill_dir = project_root / "examples" / "risky-net-egress"
    report = run_lint(skill_dir, load_policy())
    codes = {issue.code for issue in report.issues}
    assert "forbidden_pattern_2" in codes  # curl http
    assert "forbidden_pattern_4" in codes  # urllib.request.urlopen


def test_lint_accepts_zip(make_skill_zip) -> None:
    archive = make_skill_zip("brand-voice-editor")
    with open_skill_bundle(archive) as bundle:
        report = run_lint(bundle, load_policy())
    assert report.ok
