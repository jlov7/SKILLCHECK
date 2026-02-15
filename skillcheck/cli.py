"""Typer CLI for SKILLCHECK."""

from __future__ import annotations

import json
import os
import subprocess
from contextlib import contextmanager
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import typer
from rich.console import Console
from rich.table import Table

from .attest import AttestationBuilder
from .bundle import SkillBundleError, open_skill_bundle
from .lint_rules import run_lint
from .otel import emit_run_span
from .probe import ProbeRunner
from .report import ReportWriter, ReportFinding
from .sbom import generate_sbom
from .schema import Policy, find_skill_md, load_policy
from .utils import slugify

app = typer.Typer(
    add_completion=False,
    help="Audit Agent Skills bundles with lint, probe, attest, and report commands.",
)

console = Console()


@app.callback(invoke_without_command=True)
def root(ctx: typer.Context) -> None:
    """Show onboarding guidance when no command is provided."""
    if ctx.invoked_subcommand is not None:
        return
    console.print("SKILLCHECK — Audit Agent Skills", style="bold")
    console.print("Quickstart:")
    console.print("  skillcheck lint <path>")
    console.print("  skillcheck probe <path>")
    console.print("  skillcheck report .")
    console.print("Run `skillcheck help` for more.")
    raise typer.Exit(code=0)


def _resolve_output_dir(output_dir: Optional[Path]) -> Path:
    target = output_dir or (Path.cwd() / ".skillcheck")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _resolve_diff_output_dir(output_dir: Optional[Path]) -> Path:
    target = output_dir or (Path.cwd() / ".skillcheck" / "diff")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _exec_default() -> bool:
    return os.environ.get("SKILLCHECK_PROBE_EXEC", "").lower() in {"1", "true", "yes"}


@contextmanager
def _skill_dir(skill_path: Path) -> Iterator[Path]:
    try:
        with open_skill_bundle(skill_path) as bundle_dir:
            yield bundle_dir
    except SkillBundleError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _render_lint_table(report) -> None:
    table = Table(title=f"Lint Summary — {report.skill_name}", expand=True)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value")
    table.add_row("Files scanned", str(report.files_scanned))
    table.add_row("Issues", str(len(report.issues)))
    table.add_row("Violations", str(report.violations_count))
    console.print(table)
    if report.issues:
        issues = Table(title="Lint Findings", expand=True)
        issues.add_column("Severity", style="bold")
        issues.add_column("Code")
        issues.add_column("Path")
        issues.add_column("Message")
        for finding in report.issues:
            issues.add_row(
                finding.severity,
                finding.code,
                finding.path,
                finding.message,
            )
        console.print(issues)


def _render_probe_table(result) -> None:
    table = Table(title=f"Probe Summary — {result.skill_name}", expand=True)
    table.add_column("Metric", style="bold magenta")
    table.add_column("Value")
    table.add_row("Files loaded", str(result.files_loaded_count))
    table.add_row("Egress attempts", str(len(result.egress_attempts)))
    table.add_row("Disallowed writes", str(len(result.disallowed_writes)))
    console.print(table)
    if result.egress_attempts:
        egress = Table(title="Egress Attempts", expand=True)
        egress.add_column("Code")
        egress.add_column("Evidence")
        for finding in result.egress_attempts:
            egress.add_row(finding.code, finding.message)
        console.print(egress)
    if result.disallowed_writes:
        writes = Table(title="Disallowed Writes", expand=True)
        writes.add_column("Code")
        writes.add_column("Evidence")
        for finding in result.disallowed_writes:
            writes.add_row(finding.code, finding.message)
        console.print(writes)
    if result.notes:
        console.print("\n".join(result.notes), style="dim")


def _save_json(payload: dict, path: Path) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_policy(path: Optional[Path]) -> Policy:
    return load_policy(path)


def _git_changed_files(run_dir: Path, base: str, head: str) -> List[str]:
    cmd = ["git", "-C", str(run_dir), "diff", "--name-only", base, head]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown git error"
        raise typer.BadParameter(f"Unable to diff refs '{base}'..'{head}': {stderr}")
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines


def _find_skill_root(repo_root: Path, changed_path: str) -> Optional[Path]:
    candidate = repo_root / changed_path
    current = candidate if candidate.is_dir() else candidate.parent
    while True:
        if find_skill_md(current):
            return current
        if current == repo_root:
            return None
        current = current.parent


def _clear_diff_artifacts(artifact_dir: Path) -> None:
    for pattern in ("*.lint.json", "*.probe.json", "results.csv", "results.md", "results.json", "results_chart.png"):
        for artifact in artifact_dir.glob(pattern):
            artifact.unlink()


def _render_summary_table(rows) -> None:
    summary_table = Table(title="Quick Summary", expand=False)
    summary_table.add_column("Skill", style="bold")
    summary_table.add_column("Lint", justify="right")
    summary_table.add_column("Probe", justify="right")
    summary_table.add_column("Status", style="bold")
    for row in rows:
        probe_issues = row.probe_egress + row.probe_writes
        summary_table.add_row(
            row.skill_name,
            str(row.lint_violations),
            str(probe_issues),
            row.status.upper(),
        )
    console.print(summary_table)


def _gha_escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _emit_github_annotations(findings: List[ReportFinding]) -> None:
    for finding in findings:
        level = "error"
        severity = finding.severity.lower()
        if severity == "warning":
            level = "warning"
        elif severity not in {"error", "warning"}:
            level = "notice"
        file_path = _gha_escape(finding.path or "SKILL.md")
        title = _gha_escape(finding.code)
        message = _gha_escape(f"[{finding.skill_name}] {finding.message}")
        console.print(f"::{level} file={file_path},line={max(1, finding.line)},title={title}::{message}")


@app.command("help")
def help_cmd() -> None:
    """Print a compact help reference."""
    console.print("Help — SKILLCHECK", style="bold")
    console.print("Quickstart:")
    console.print("  skillcheck lint <path>")
    console.print("  skillcheck probe <path>")
    console.print("  skillcheck report .")
    console.print("Docs: docs/help.md")


@app.command()
def lint(
    skill_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=True),
    policy: Optional[Path] = typer.Option(None, "--policy", "-p", help="Path to policy YAML."),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", help="Directory for lint artifacts (default: ./.skillcheck)."
    ),
) -> None:
    """Run static lint against a Skill bundle."""
    policy_obj = _load_policy(policy)
    with _skill_dir(skill_path) as bundle_dir:
        report = run_lint(bundle_dir, policy_obj)
    _render_lint_table(report)
    artifacts_dir = _resolve_output_dir(output_dir)
    artifact_path = artifacts_dir / f"{slugify(report.skill_name)}.lint.json"
    _save_json(report.to_dict(), artifact_path)
    emit_run_span(
        "lint",
        report.skill_name,
        {
            "skill.version": report.skill_version or "",
            "lint.violations_count": report.violations_count,
            "lint.issue_count": len(report.issues),
        },
    )
    console.print(f"Lint report saved to {artifact_path}", style="green")
    raise typer.Exit(code=0 if report.ok else 1)


@app.command()
def probe(
    skill_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=True),
    policy: Optional[Path] = typer.Option(None, "--policy", "-p", help="Path to policy YAML."),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", help="Directory for probe artifacts (default: ./.skillcheck)."
    ),
    exec_probe: bool = typer.Option(
        _exec_default(),
        "--exec/--no-exec",
        help="Execute Python scripts in an isolated sandbox runner.",
    ),
) -> None:
    """Run dynamic probe heuristics inside an ephemeral sandbox."""
    policy_obj = _load_policy(policy)
    with _skill_dir(skill_path) as bundle_dir:
        runner = ProbeRunner(policy_obj, enable_exec=exec_probe)
        result = runner.run(bundle_dir)
    _render_probe_table(result)
    artifacts_dir = _resolve_output_dir(output_dir)
    artifact_path = artifacts_dir / f"{slugify(result.skill_name)}.probe.json"
    _save_json(result.to_dict(), artifact_path)
    emit_run_span(
        "probe",
        result.skill_name,
        {
            "skill.version": result.skill_version or "",
            "skill.files_loaded_count": result.files_loaded_count,
            "probe.egress_attempts": len(result.egress_attempts),
            "probe.disallowed_writes": len(result.disallowed_writes),
        },
    )
    console.print(f"Probe report saved to {artifact_path}", style="green")
    raise typer.Exit(code=0 if result.ok else 1)


@app.command()
def attest(
    skill_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=True),
    policy: Optional[Path] = typer.Option(None, "--policy", "-p", help="Path to policy YAML."),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", help="Directory for attestation artifacts (default: ./.skillcheck)."
    ),
    exec_probe: bool = typer.Option(
        _exec_default(),
        "--exec/--no-exec",
        help="Execute Python scripts in an isolated sandbox runner.",
    ),
) -> None:
    """Generate SBOM and attestation manifest for a Skill."""
    policy_obj = _load_policy(policy)
    artifacts_dir = _resolve_output_dir(output_dir)
    with _skill_dir(skill_path) as bundle_dir:
        report = run_lint(bundle_dir, policy_obj)
        result = ProbeRunner(policy_obj, enable_exec=exec_probe).run(bundle_dir)
        artifact_stem = slugify(report.skill_name)
        sbom_path = generate_sbom(bundle_dir, artifacts_dir / f"{artifact_stem}.sbom.json")
        builder = AttestationBuilder(policy_obj)
        attestation_path = builder.build(
            bundle_dir,
            report,
            result,
            sbom_path,
            artifacts_dir,
            artifact_stem=artifact_stem,
            source_path=str(skill_path),
        )
    console.print(f"SBOM saved to {sbom_path}", style="green")
    console.print(f"Attestation saved to {attestation_path}", style="green")
    emit_run_span(
        "attest",
        report.skill_name,
        {
            "skill.version": report.skill_version or "",
            "lint.violations_count": report.violations_count,
            "probe.egress_attempts": len(result.egress_attempts),
            "probe.disallowed_writes": len(result.disallowed_writes),
        },
    )


@app.command()
def report(
    run_dir: Path = typer.Argument(
        ..., exists=True, file_okay=False, help="Directory containing skill artifacts (e.g. repo root)."
    ),
    artifacts_dir: Optional[Path] = typer.Option(
        None,
        "--artifacts",
        help="Directory with lint/probe/attestation JSON (default: <run_dir>/.skillcheck).",
    ),
    fail_on_failures: bool = typer.Option(
        False,
        "--fail-on-failures/--no-fail-on-failures",
        help="Exit with non-zero status if any skill fails lint or probe checks.",
    ),
    summary: bool = typer.Option(
        False,
        "--summary/--no-summary",
        help="Print a condensed PASS/FAIL table to the terminal.",
    ),
    sarif: bool = typer.Option(
        False,
        "--sarif/--no-sarif",
        help="Emit SARIF findings to <artifacts>/results.sarif.",
    ),
    github_annotations: bool = typer.Option(
        False,
        "--github-annotations/--no-github-annotations",
        help="Print GitHub Actions annotation lines for findings.",
    ),
) -> None:
    """Produce CSV and Markdown report by aggregating prior runs."""
    artifact_root = artifacts_dir or (run_dir / ".skillcheck")
    writer = ReportWriter(artifact_root)
    result = writer.write(write_sarif=sarif)
    if not result.rows:
        console.print("No skill artifacts found. Run lint/probe first.", style="yellow")
    console.print(f"Report CSV: {result.csv_path}", style="green")
    console.print(f"Report Markdown: {result.md_path}", style="green")
    console.print(f"Report JSON: {result.json_path}", style="green")
    if result.sarif_path:
        console.print(f"Report SARIF: {result.sarif_path}", style="green")
    console.print(
        f"Summary — total: {result.summary.total}, pass: {result.summary.pass_count}, fail: {result.summary.fail_count}",
        style="cyan",
    )
    if summary:
        if not result.rows:
            console.print("No skills found in artifacts.", style="yellow")
        else:
            _render_summary_table(result.rows)
    emit_run_span(
        "report",
        "aggregate",
        {"report.skill_count": len(result.rows)},
    )
    if github_annotations and result.findings:
        _emit_github_annotations(result.findings)
    if fail_on_failures and result.summary.fail_count:
        raise typer.Exit(code=1)


@app.command()
def diff(
    run_dir: Path = typer.Argument(
        ..., exists=True, file_okay=False, help="Git repository root containing skills."
    ),
    base: str = typer.Option("HEAD~1", "--base", help="Base git ref for changed-files diff."),
    head: str = typer.Option("HEAD", "--head", help="Head git ref for changed-files diff."),
    policy: Optional[Path] = typer.Option(None, "--policy", "-p", help="Path to policy YAML."),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        help="Directory for diff artifacts (default: ./.skillcheck/diff).",
    ),
    exec_probe: bool = typer.Option(
        _exec_default(),
        "--exec/--no-exec",
        help="Execute Python scripts in an isolated sandbox runner.",
    ),
    fail_on_failures: bool = typer.Option(
        False,
        "--fail-on-failures/--no-fail-on-failures",
        help="Exit with non-zero status if any changed skill fails lint or probe checks.",
    ),
    summary: bool = typer.Option(
        True,
        "--summary/--no-summary",
        help="Print a condensed PASS/FAIL table for changed skills.",
    ),
) -> None:
    """Run lint/probe only for skills touched between two git refs."""
    changed_files = _git_changed_files(run_dir, base, head)
    changed_skills: Dict[Path, List[str]] = defaultdict(list)
    for changed_file in changed_files:
        skill_root = _find_skill_root(run_dir, changed_file)
        if skill_root is None:
            continue
        changed_skills[skill_root].append(changed_file)

    if not changed_skills:
        console.print(f"No changed skill files detected between {base} and {head}.", style="yellow")
        raise typer.Exit(code=0)

    policy_obj = _load_policy(policy)
    artifacts_dir = _resolve_diff_output_dir(output_dir)
    _clear_diff_artifacts(artifacts_dir)

    for skill_root, files in sorted(changed_skills.items(), key=lambda item: str(item[0])):
        lint_report = run_lint(skill_root, policy_obj)
        probe_report = ProbeRunner(policy_obj, enable_exec=exec_probe).run(skill_root)
        stem = slugify(lint_report.skill_name)
        _save_json(lint_report.to_dict(), artifacts_dir / f"{stem}.lint.json")
        _save_json(probe_report.to_dict(), artifacts_dir / f"{stem}.probe.json")
        console.print(f"Audited {lint_report.skill_name} ({len(files)} changed files)", style="cyan")

    writer = ReportWriter(artifacts_dir)
    result = writer.write()
    console.print(f"Diff report CSV: {result.csv_path}", style="green")
    console.print(f"Diff report Markdown: {result.md_path}", style="green")
    console.print(f"Diff report JSON: {result.json_path}", style="green")
    console.print(
        f"Changed skills audited: {result.summary.total}, pass: {result.summary.pass_count}, fail: {result.summary.fail_count}",
        style="cyan",
    )
    if summary and result.rows:
        _render_summary_table(result.rows)
    if fail_on_failures and result.summary.fail_count:
        raise typer.Exit(code=1)


def main() -> None:
    """Entrypoint for console script."""
    app()


if __name__ == "__main__":
    main()
