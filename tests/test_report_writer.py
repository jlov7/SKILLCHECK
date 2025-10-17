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

    safe_dir = project_root / "examples" / "safe_brand_guidelines"
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
