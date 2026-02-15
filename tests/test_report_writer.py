import json
from pathlib import Path

from skillcheck.lint_rules import run_lint
from skillcheck.probe import ProbeRunner
from skillcheck.report import ReportWriter
from skillcheck.schema import load_policy
from skillcheck.utils import slugify


def test_report_writer_outputs_json(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    artifacts = tmp_path / ".skillcheck"
    artifacts.mkdir()
    policy = load_policy()

    safe_dir = project_root / "examples" / "brand-voice-editor"
    lint_report = run_lint(safe_dir, policy)
    probe_report = ProbeRunner(policy).run(safe_dir)
    slug = slugify(lint_report.skill_name)
    (artifacts / f"{slug}.lint.json").write_text(json.dumps(lint_report.to_dict()), encoding="utf-8")
    (artifacts / f"{slug}.probe.json").write_text(json.dumps(probe_report.to_dict()), encoding="utf-8")

    writer = ReportWriter(artifacts)
    result = writer.write()

    assert result.summary.total == 1
    assert result.summary.pass_count == 1
    assert result.summary.fail_count == 0
    assert result.json_path.exists()

    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["total"] == 1
    assert payload["rows"][0]["skill_name"] == lint_report.skill_name


def test_report_writer_outputs_sarif(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    artifacts = tmp_path / ".skillcheck"
    artifacts.mkdir()
    policy = load_policy()

    risky_dir = project_root / "examples" / "risky-net-egress"
    lint_report = run_lint(risky_dir, policy)
    probe_report = ProbeRunner(policy).run(risky_dir)
    slug = slugify(lint_report.skill_name)
    (artifacts / f"{slug}.lint.json").write_text(json.dumps(lint_report.to_dict()), encoding="utf-8")
    (artifacts / f"{slug}.probe.json").write_text(json.dumps(probe_report.to_dict()), encoding="utf-8")

    writer = ReportWriter(artifacts)
    result = writer.write(write_sarif=True)

    assert result.sarif_path is not None
    assert result.sarif_path.exists()
    sarif = json.loads(result.sarif_path.read_text(encoding="utf-8"))
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"], "Expected SARIF findings"


def test_report_writer_includes_trust_score(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    artifacts = tmp_path / ".skillcheck"
    artifacts.mkdir()
    policy = load_policy()

    safe_dir = project_root / "examples" / "brand-voice-editor"
    lint_report = run_lint(safe_dir, policy)
    probe_report = ProbeRunner(policy).run(safe_dir)
    slug = slugify(lint_report.skill_name)
    (artifacts / f"{slug}.lint.json").write_text(json.dumps(lint_report.to_dict()), encoding="utf-8")
    (artifacts / f"{slug}.probe.json").write_text(json.dumps(probe_report.to_dict()), encoding="utf-8")

    writer = ReportWriter(artifacts)
    result = writer.write()
    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert "avg_trust_score" in payload["summary"]
    assert "trust_score" in payload["rows"][0]
