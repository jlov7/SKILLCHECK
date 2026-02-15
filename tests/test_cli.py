import json
from pathlib import Path

from typer.testing import CliRunner

from skillcheck.cli import app
from skillcheck.lint_rules import run_lint
from skillcheck.probe import ProbeRunner
from skillcheck.schema import load_policy
from skillcheck.utils import slugify


runner = CliRunner()


def test_cli_lint_zip(make_skill_zip) -> None:
    archive = make_skill_zip("brand-voice-editor")
    result = runner.invoke(app, ["lint", str(archive)])
    assert result.exit_code == 0


def test_cli_probe_zip_failure(make_skill_zip) -> None:
    archive = make_skill_zip("risky-net-egress")
    result = runner.invoke(
        app,
        ["probe", "--exec", str(archive)],
        env={"SKILLCHECK_PROBE_EXEC": "1"},
    )
    assert result.exit_code != 0


def test_cli_report_fail_on_failures(tmp_path: Path) -> None:
    artifact_dir = tmp_path / ".skillcheck"
    artifact_dir.mkdir()
    project_root = Path(__file__).resolve().parents[1]
    policy = load_policy()

    # Safe skill (pass)
    safe_dir = project_root / "examples" / "brand-voice-editor"
    safe_lint = run_lint(safe_dir, policy)
    safe_probe = ProbeRunner(policy).run(safe_dir)
    safe_slug = slugify(safe_lint.skill_name)
    (artifact_dir / f"{safe_slug}.lint.json").write_text(json.dumps(safe_lint.to_dict()), encoding="utf-8")
    (artifact_dir / f"{safe_slug}.probe.json").write_text(json.dumps(safe_probe.to_dict()), encoding="utf-8")

    # Risky skill (fail) — copy probe json only to simulate failure
    risky_dir = project_root / "examples" / "risky-net-egress"
    risky_lint = run_lint(risky_dir, policy)
    risky_probe = ProbeRunner(policy).run(risky_dir)
    risky_slug = slugify(risky_lint.skill_name)
    (artifact_dir / f"{risky_slug}.lint.json").write_text(json.dumps(risky_lint.to_dict()), encoding="utf-8")
    (artifact_dir / f"{risky_slug}.probe.json").write_text(json.dumps(risky_probe.to_dict()), encoding="utf-8")

    env = {}
    result = runner.invoke(
        app,
        [
            "report",
            str(tmp_path),
            "--artifacts",
            str(artifact_dir),
            "--fail-on-failures",
        ],
        env=env,
    )
    assert result.exit_code == 1

    summary_result = runner.invoke(
        app,
        [
            "report",
            str(tmp_path),
            "--artifacts",
            str(artifact_dir),
            "--summary",
        ],
        env=env,
    )
    assert summary_result.exit_code == 0
    assert "Quick Summary" in summary_result.stdout
    assert "brand-voice-editor" in summary_result.stdout


def test_cli_first_run_shows_quickstart() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Quickstart" in result.output
    assert "skillcheck lint" in result.output


def test_cli_help_command_outputs_guidance() -> None:
    result = runner.invoke(app, ["help"])
    assert result.exit_code == 0
    assert "Help" in result.output
    assert "docs/help.md" in result.output


def test_report_empty_state_message(tmp_path: Path) -> None:
    result = runner.invoke(app, ["report", str(tmp_path), "--summary"])
    assert result.exit_code == 0
    assert "No skill artifacts found" in result.output
