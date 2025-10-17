"""Aggregate lint/probe results into CSV and Markdown reports."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    import matplotlib.pyplot as plt  # type: ignore

    _HAS_MATPLOTLIB = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_MATPLOTLIB = False


@dataclass
class ReportRow:
    skill_name: str
    skill_version: str
    lint_violations: int
    lint_issues: int
    probe_egress: int
    probe_writes: int
    policy_hash: str
    signature_mode: str

    @property
    def status(self) -> str:
        return "pass" if self.lint_violations == 0 and self.probe_egress == 0 and self.probe_writes == 0 else "fail"


@dataclass
class ReportSummary:
    total: int
    pass_count: int
    fail_count: int


@dataclass
class ReportResult:
    rows: List[ReportRow]
    summary: ReportSummary
    csv_path: Path
    md_path: Path
    chart_path: Optional[Path]
    json_path: Path


class ReportWriter:
    """Collate JSON artifacts and write tabular reports."""

    def __init__(self, artifact_dir: Path):
        self.artifact_dir = artifact_dir
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def _load_json_files(self, suffix: str) -> Dict[str, dict]:
        data: Dict[str, dict] = {}
        for json_path in self.artifact_dir.glob(f"*{suffix}.json"):
            content = json.loads(json_path.read_text(encoding="utf-8"))
            skill_name = content.get("skill", {}).get("name") or json_path.stem.split(".")[0]
            data[skill_name] = content
        return data

    def _collect_rows(self) -> List[ReportRow]:
        lint = self._load_json_files(".lint")
        probe = self._load_json_files(".probe")
        attest = self._load_json_files(".attestation")
        rows: List[ReportRow] = []
        for skill_name in sorted(set(lint.keys()) | set(probe.keys()) | set(attest.keys())):
            lint_entry = lint.get(skill_name, {})
            probe_entry = probe.get(skill_name, {})
            att_entry = attest.get(skill_name, {})
            summary = lint_entry.get("summary", {})
            probe_summary = probe_entry.get("summary", {})
            rows.append(
                ReportRow(
                    skill_name=skill_name,
                    skill_version=lint_entry.get("skill", {}).get("version") or "",
                    lint_violations=int(summary.get("violations_count", 0)),
                    lint_issues=int(summary.get("issue_count", 0)),
                    probe_egress=int(probe_summary.get("egress_attempts", 0)),
                    probe_writes=int(probe_summary.get("disallowed_writes", 0)),
                    policy_hash=att_entry.get("policy", {}).get("sha256", ""),
                    signature_mode=att_entry.get("signature", {}).get("mode", ""),
                )
            )
        return rows

    def _write_csv(self, rows: List[ReportRow]) -> Path:
        csv_path = self.artifact_dir / "results.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "skill_name",
                    "skill_version",
                    "lint_violations",
                    "lint_issues",
                    "probe_egress",
                    "probe_disallowed_writes",
                    "policy_hash",
                    "signature_mode",
                    "status",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row.skill_name,
                        row.skill_version,
                        row.lint_violations,
                        row.lint_issues,
                        row.probe_egress,
                        row.probe_writes,
                        row.policy_hash,
                        row.signature_mode,
                        row.status,
                    ]
                )
        return csv_path

    def _write_markdown(self, rows: List[ReportRow], chart_path: Optional[Path], summary: ReportSummary) -> Path:
        md_path = self.artifact_dir / "results.md"
        lines = [
            "# SKILLCHECK Report",
            "",
            f"Total skills audited: **{len(rows)}**",
            f"- Passes: **{summary.pass_count}**",
            f"- Failures: **{summary.fail_count}**",
            "",
            "| Skill | Version | Lint Violations | Lint Issues | Egress Attempts | Disallowed Writes | Policy Hash | Signature | Status |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in rows:
            lines.append(
                f"| {row.skill_name} | {row.skill_version or '—'} | {row.lint_violations} | {row.lint_issues} | "
                f"{row.probe_egress} | {row.probe_writes} | {row.policy_hash or '—'} | {row.signature_mode or '—'} | {row.status.upper()} |"
            )
        if chart_path:
            lines.append("")
            lines.append(f"![Lint vs Probe]({chart_path.name})")
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return md_path

    def _write_json(self, rows: List[ReportRow], summary: ReportSummary) -> Path:
        json_path = self.artifact_dir / "results.json"
        payload = {
            "summary": {
                "total": summary.total,
                "pass_count": summary.pass_count,
                "fail_count": summary.fail_count,
            },
            "rows": [
                {
                    "skill_name": row.skill_name,
                    "skill_version": row.skill_version,
                    "lint_violations": row.lint_violations,
                    "lint_issues": row.lint_issues,
                    "probe_egress": row.probe_egress,
                    "probe_disallowed_writes": row.probe_writes,
                    "policy_hash": row.policy_hash,
                    "signature_mode": row.signature_mode,
                    "status": row.status,
                }
                for row in rows
            ],
        }
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return json_path

    def _summarize(self, rows: List[ReportRow]) -> ReportSummary:
        pass_count = sum(1 for row in rows if row.status == "pass")
        fail_count = sum(1 for row in rows if row.status != "pass")
        return ReportSummary(total=len(rows), pass_count=pass_count, fail_count=fail_count)

    def _write_chart(self, rows: List[ReportRow]) -> Optional[Path]:
        if not _HAS_MATPLOTLIB or not rows:
            return None
        chart_path = self.artifact_dir / "results_chart.png"
        labels = [row.skill_name for row in rows]
        lint_vals = [row.lint_violations for row in rows]
        probe_vals = [row.probe_egress + row.probe_writes for row in rows]
        x = range(len(rows))
        plt.figure(figsize=(max(6, len(rows) * 1.2), 4))
        plt.bar(x, lint_vals, width=0.4, label="Lint violations")
        plt.bar([pos + 0.4 for pos in x], probe_vals, width=0.4, label="Probe issues")
        plt.xticks([pos + 0.2 for pos in x], labels, rotation=45, ha="right")
        plt.tight_layout()
        plt.legend()
        plt.savefig(chart_path, dpi=150)
        plt.close()
        return chart_path

    def write(self) -> ReportResult:
        rows = self._collect_rows()
        summary = self._summarize(rows)
        csv_path = self._write_csv(rows)
        chart_path = self._write_chart(rows)
        md_path = self._write_markdown(rows, chart_path, summary)
        json_path = self._write_json(rows, summary)
        return ReportResult(rows=rows, summary=summary, csv_path=csv_path, md_path=md_path, chart_path=chart_path, json_path=json_path)
