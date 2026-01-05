from pathlib import Path

from skillcheck.bundle import open_skill_bundle
from skillcheck.probe import ProbeRunner
from skillcheck.schema import load_policy


def test_probe_safe_skill() -> None:
    project_root = Path(__file__).resolve().parents[1]
    skill_dir = project_root / "examples" / "brand-voice-editor"
    result = ProbeRunner(load_policy()).run(skill_dir)
    assert result.files_loaded_count >= 1
    assert not result.egress_attempts
    assert not result.disallowed_writes


def test_probe_risky_skill_detects_issues() -> None:
    project_root = Path(__file__).resolve().parents[1]
    skill_dir = project_root / "examples" / "risky-net-egress"
    result = ProbeRunner(load_policy()).run(skill_dir)
    assert result.egress_attempts, "Expected egress attempts to be detected"
    assert result.disallowed_writes, "Expected disallowed writes to be detected"


def test_probe_exec_mode_enforces_sandbox() -> None:
    project_root = Path(__file__).resolve().parents[1]
    skill_dir = project_root / "examples" / "risky-net-egress"
    result = ProbeRunner(load_policy(), enable_exec=True).run(skill_dir)
    codes = {finding.code for finding in result.egress_attempts}
    write_codes = {finding.code for finding in result.disallowed_writes}
    assert "EGRESS_SANDBOX" in codes
    assert "WRITE_SANDBOX" in write_codes


def test_probe_handles_zip(make_skill_zip) -> None:
    archive = make_skill_zip("brand-voice-editor")
    with open_skill_bundle(archive) as bundle:
        result = ProbeRunner(load_policy()).run(bundle)
    assert result.files_loaded_count >= 1
