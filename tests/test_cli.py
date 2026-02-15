import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from skillcheck.cli import app
from skillcheck.lint_rules import run_lint
from skillcheck.probe import ProbeRunner
from skillcheck.schema import load_policy
from skillcheck.utils import slugify


runner = CliRunner()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


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
    assert "skillcheck fix" in result.output
    assert "docs/help.md" in result.output


def test_report_empty_state_message(tmp_path: Path) -> None:
    result = runner.invoke(app, ["report", str(tmp_path), "--summary"])
    assert result.exit_code == 0
    assert "No skill artifacts found" in result.output


def test_help_doc_exists() -> None:
    assert Path("docs/help.md").exists()


def test_build_dependency_declared() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text())
    dev_deps = data["project"]["optional-dependencies"]["dev"]
    assert any(dep.startswith("build") for dep in dev_deps)


def test_readme_mentions_deploy_and_env_vars() -> None:
    content = Path("README.md").read_text()
    assert "Deploy" in content or "Release" in content
    assert "Environment variables" in content or "Env vars" in content


def _init_git_repo_with_two_skills(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for skill_name in ("skill-a", "skill-b"):
        skill_dir = repo / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: {skill_name}
description: "Skill {skill_name}"
---

# {skill_name}
""",
            encoding="utf-8",
        )
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)
    (repo / "skill-a" / "notes.md").write_text("changed", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "change skill a"], cwd=repo, check=True, capture_output=True, text=True)
    return repo


def _init_git_repo_with_broken_skill(tmp_path: Path) -> Path:
    repo = tmp_path / "broken-repo"
    repo.mkdir()
    skill_dir = repo / "broken-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: BAD Skill !!!
description: "Broken skill"
unknown_field: true
---

# Broken
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)
    (skill_dir / "notes.md").write_text("changed", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "change broken skill"], cwd=repo, check=True, capture_output=True, text=True)
    return repo


def test_cli_diff_audits_only_changed_skills(tmp_path: Path) -> None:
    repo = _init_git_repo_with_two_skills(tmp_path)
    out_dir = repo / ".skillcheck-diff"
    result = runner.invoke(
        app,
        [
            "diff",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
            "--output-dir",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0
    assert (out_dir / "skill-a.lint.json").exists()
    assert (out_dir / "skill-a.probe.json").exists()
    assert not (out_dir / "skill-b.lint.json").exists()
    payload = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
    assert payload["summary"]["total"] == 1


def test_cli_diff_no_changed_skills(tmp_path: Path) -> None:
    repo = _init_git_repo_with_two_skills(tmp_path)
    result = runner.invoke(
        app,
        [
            "diff",
            str(repo),
            "--base",
            "HEAD",
            "--head",
            "HEAD",
        ],
    )
    assert result.exit_code == 0
    assert "No changed skill files detected" in result.stdout


def test_cli_fix_dry_run_outputs_artifact(tmp_path: Path) -> None:
    repo = _init_git_repo_with_broken_skill(tmp_path)
    out_dir = repo / ".skillcheck-fix"
    result = runner.invoke(
        app,
        [
            "fix",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
            "--output-dir",
            str(out_dir),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    artifact = out_dir / "fix.results.json"
    assert artifact.exists()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["summary"]["skills_considered"] == 1
    assert payload["summary"]["skills_changed"] == 0


def test_cli_fix_no_changed_skills_still_writes_artifact(tmp_path: Path) -> None:
    repo = _init_git_repo_with_broken_skill(tmp_path)
    out_dir = repo / ".skillcheck-fix"
    result = runner.invoke(
        app,
        [
            "fix",
            str(repo),
            "--base",
            "HEAD",
            "--head",
            "HEAD",
            "--output-dir",
            str(out_dir),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "No changed skill files detected" in result.stdout
    artifact = out_dir / "fix.results.json"
    assert artifact.exists()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["summary"]["skills_considered"] == 0


def test_cli_fix_apply_updates_skill(tmp_path: Path) -> None:
    repo = _init_git_repo_with_broken_skill(tmp_path)
    result = runner.invoke(
        app,
        [
            "fix",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
            "--apply",
        ],
    )
    assert result.exit_code == 0
    fixed_content = (repo / "broken-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "name: broken-skill" in fixed_content
    assert "unknown_field" not in fixed_content


def test_cli_fix_rejects_pr_without_push(tmp_path: Path) -> None:
    repo = _init_git_repo_with_broken_skill(tmp_path)
    result = runner.invoke(
        app,
        [
            "fix",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
            "--apply",
            "--pr",
        ],
    )
    assert result.exit_code == 2
    assert "requires --push" in result.output


def test_cli_fix_rejects_push_without_commit(tmp_path: Path) -> None:
    repo = _init_git_repo_with_broken_skill(tmp_path)
    result = runner.invoke(
        app,
        [
            "fix",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
            "--apply",
            "--push",
        ],
    )
    assert result.exit_code == 2
    assert "requires --commit" in result.output


def test_cli_fix_commit_creates_commit(tmp_path: Path) -> None:
    repo = _init_git_repo_with_broken_skill(tmp_path)
    result = runner.invoke(
        app,
        [
            "fix",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
            "--apply",
            "--commit",
            "--branch-name",
            "autofix-test",
        ],
    )
    assert result.exit_code == 0
    log = subprocess.run(
        ["git", "log", "--oneline", "-n", "1"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "skillcheck: auto remediate changed skills" in log.stdout


def test_cli_report_outputs_sarif_and_annotations(tmp_path: Path) -> None:
    artifact_dir = tmp_path / ".skillcheck"
    artifact_dir.mkdir()
    project_root = Path(__file__).resolve().parents[1]
    policy = load_policy()
    risky_dir = project_root / "examples" / "risky-net-egress"
    risky_lint = run_lint(risky_dir, policy)
    risky_probe = ProbeRunner(policy).run(risky_dir)
    risky_slug = slugify(risky_lint.skill_name)
    (artifact_dir / f"{risky_slug}.lint.json").write_text(json.dumps(risky_lint.to_dict()), encoding="utf-8")
    (artifact_dir / f"{risky_slug}.probe.json").write_text(json.dumps(risky_probe.to_dict()), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "report",
            str(tmp_path),
            "--artifacts",
            str(artifact_dir),
            "--sarif",
            "--github-annotations",
        ],
    )
    assert result.exit_code == 0
    assert (artifact_dir / "results.sarif").exists()
    assert "::warning" in result.stdout or "::error" in result.stdout


def test_cli_lint_supports_policy_pack_and_version() -> None:
    project_root = Path(__file__).resolve().parents[1]
    safe_dir = project_root / "examples" / "brand-voice-editor"
    result = runner.invoke(
        app,
        [
            "lint",
            str(safe_dir),
            "--policy-pack",
            "balanced",
            "--policy-version",
            "2",
        ],
    )
    assert result.exit_code == 0


def test_cli_remediate_outputs_guidance() -> None:
    result = runner.invoke(app, ["remediate", "EGRESS_SANDBOX"])
    assert result.exit_code == 0
    assert "Recommended fixes" in result.stdout
    assert "network" in result.stdout.lower()


def test_cli_report_fail_on_low_trust(tmp_path: Path) -> None:
    artifact_dir = tmp_path / ".skillcheck"
    artifact_dir.mkdir()
    project_root = Path(__file__).resolve().parents[1]
    policy = load_policy()
    risky_dir = project_root / "examples" / "risky-net-egress"
    risky_lint = run_lint(risky_dir, policy)
    risky_probe = ProbeRunner(policy).run(risky_dir)
    risky_slug = slugify(risky_lint.skill_name)
    (artifact_dir / f"{risky_slug}.lint.json").write_text(json.dumps(risky_lint.to_dict()), encoding="utf-8")
    (artifact_dir / f"{risky_slug}.probe.json").write_text(json.dumps(risky_probe.to_dict()), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "report",
            str(tmp_path),
            "--artifacts",
            str(artifact_dir),
            "--min-trust-score",
            "90",
            "--fail-on-low-trust",
        ],
    )
    assert result.exit_code == 1


def test_cli_report_release_gate_strict(tmp_path: Path) -> None:
    artifact_dir = tmp_path / ".skillcheck"
    artifact_dir.mkdir()
    project_root = Path(__file__).resolve().parents[1]
    policy = load_policy()
    risky_dir = project_root / "examples" / "risky-net-egress"
    risky_lint = run_lint(risky_dir, policy)
    risky_probe = ProbeRunner(policy).run(risky_dir)
    risky_slug = slugify(risky_lint.skill_name)
    (artifact_dir / f"{risky_slug}.lint.json").write_text(json.dumps(risky_lint.to_dict()), encoding="utf-8")
    (artifact_dir / f"{risky_slug}.probe.json").write_text(json.dumps(risky_probe.to_dict()), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "report",
            str(tmp_path),
            "--artifacts",
            str(artifact_dir),
            "--release-gate",
            "strict",
        ],
    )
    assert result.exit_code == 1
