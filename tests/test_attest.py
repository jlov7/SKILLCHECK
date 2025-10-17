import json
from pathlib import Path

from skillcheck.attest import AttestationBuilder
from skillcheck.bundle import open_skill_bundle
from skillcheck.lint_rules import run_lint
from skillcheck.probe import ProbeRunner
from skillcheck.schema import load_policy
from skillcheck.sbom import generate_sbom


def test_attestation_serializes_policy(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    skill_dir = project_root / "examples" / "safe_brand_guidelines"
    policy = load_policy()
    lint_report = run_lint(skill_dir, policy)
    probe_result = ProbeRunner(policy).run(skill_dir)
    artifacts = tmp_path / ".skillcheck"
    artifacts.mkdir()
    sbom_path = generate_sbom(skill_dir, artifacts / "safe.sbom.json")
    builder = AttestationBuilder(policy)
    attestation_path = builder.build(
        skill_dir,
        lint_report,
        probe_result,
        sbom_path,
        artifacts,
        artifact_stem="safe",
    )
    data = json.loads(attestation_path.read_text(encoding="utf-8"))
    patterns = data["policy"]["forbidden_patterns"]
    assert isinstance(patterns, list)
    assert isinstance(patterns[0]["pattern"], str)
    assert data["signature"]["mode"] == "unsigned"


def test_attestation_from_zip(tmp_path: Path, make_skill_zip) -> None:
    archive = make_skill_zip("safe_brand_guidelines")
    policy = load_policy()
    with open_skill_bundle(archive) as bundle:
        lint_report = run_lint(bundle, policy)
        probe_result = ProbeRunner(policy).run(bundle)
        artifacts = tmp_path / ".skillcheck"
        artifacts.mkdir()
        sbom_path = generate_sbom(bundle, artifacts / "safe.sbom.json")
        builder = AttestationBuilder(policy)
        attestation_path = builder.build(
            bundle,
            lint_report,
            probe_result,
            sbom_path,
            artifacts,
            artifact_stem="safe",
            source_path=str(archive),
        )
    payload = json.loads(attestation_path.read_text(encoding="utf-8"))
    assert payload["skill"]["path"] == str(archive)
