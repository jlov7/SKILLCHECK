"""Aggregate lint/probe results into CSV and Markdown reports."""

from __future__ import annotations

import csv
import json
import re
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
    waivers_count: int
    trust_score: float

    @property
    def status(self) -> str:
        return "pass" if self.lint_violations == 0 and self.probe_egress == 0 and self.probe_writes == 0 else "fail"


@dataclass
class ReportSummary:
    total: int
    pass_count: int
    fail_count: int
    avg_trust_score: float
    min_trust_score: float


@dataclass
class ReportResult:
    rows: List[ReportRow]
    findings: List["ReportFinding"]
    summary: ReportSummary
    csv_path: Path
    md_path: Path
    chart_path: Optional[Path]
    json_path: Path
    sarif_path: Optional[Path]


@dataclass
class ReportFinding:
    skill_name: str
    code: str
    message: str
    path: str
    line: int
    severity: str
    source: str


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

    def _collect_rows(self, lint: Dict[str, dict], probe: Dict[str, dict], attest: Dict[str, dict]) -> List[ReportRow]:
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
                    waivers_count=len(att_entry.get("policy", {}).get("waivers", []) or []),
                    trust_score=0.0,
                )
            )
        for row in rows:
            row.trust_score = self._calculate_trust_score(row)
        return rows

    def _calculate_trust_score(self, row: ReportRow) -> float:
        score = 100.0
        score -= 15.0 * row.lint_violations
        score -= 20.0 * row.probe_egress
        score -= 20.0 * row.probe_writes
        score -= 2.0 * row.waivers_count
        if row.signature_mode == "sigstore":
            score += 3.0
        score = max(0.0, min(100.0, score))
        return round(score, 2)

    def _collect_findings(self, lint: Dict[str, dict], probe: Dict[str, dict]) -> List[ReportFinding]:
        findings: List[ReportFinding] = []
        for skill_name, lint_entry in lint.items():
            for issue in lint_entry.get("issues", []) or []:
                if not isinstance(issue, dict):
                    continue
                severity = str(issue.get("severity") or "error")
                path = str(issue.get("path") or "SKILL.md")
                message = str(issue.get("message") or "")
                code = str(issue.get("code") or "LINT")
                findings.append(
                    ReportFinding(
                        skill_name=skill_name,
                        code=code,
                        message=message,
                        path=path,
                        line=1,
                        severity=severity,
                        source="lint",
                    )
                )
        for skill_name, probe_entry in probe.items():
            for section, source_code in (("egress_attempts", "probe-egress"), ("disallowed_writes", "probe-write")):
                for item in probe_entry.get(section, []) or []:
                    if not isinstance(item, dict):
                        continue
                    code = str(item.get("code") or "PROBE")
                    message = str(item.get("message") or "")
                    path, detail = self._extract_probe_path(message)
                    findings.append(
                        ReportFinding(
                            skill_name=skill_name,
                            code=code,
                            message=detail,
                            path=path,
                            line=1,
                            severity="error",
                            source=source_code,
                        )
                    )
        return findings

    def _extract_probe_path(self, message: str) -> tuple[str, str]:
        match = re.match(r"^(?P<path>[^:\n]+):\s*(?P<detail>.+)$", message)
        if not match:
            return "SKILL.md", message
        path = (match.group("path") or "").strip()
        detail = (match.group("detail") or message).strip()
        if "/" in path or "." in path:
            return path, detail
        return "SKILL.md", message

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
                    "waivers_count",
                    "trust_score",
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
                        row.waivers_count,
                        row.trust_score,
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
            "| Skill | Version | Lint Violations | Lint Issues | Egress Attempts | Disallowed Writes | Trust Score | Policy Hash | Signature | Status |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in rows:
            lines.append(
                f"| {row.skill_name} | {row.skill_version or '—'} | {row.lint_violations} | {row.lint_issues} | "
                f"{row.probe_egress} | {row.probe_writes} | {row.trust_score:.2f} | {row.policy_hash or '—'} | {row.signature_mode or '—'} | {row.status.upper()} |"
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
                "avg_trust_score": summary.avg_trust_score,
                "min_trust_score": summary.min_trust_score,
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
                    "waivers_count": row.waivers_count,
                    "trust_score": row.trust_score,
                    "status": row.status,
                }
                for row in rows
            ],
        }
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return json_path

    def _write_sarif(self, findings: List[ReportFinding]) -> Path:
        sarif_path = self.artifact_dir / "results.sarif"
        rules: Dict[str, Dict[str, object]] = {}
        results: List[Dict[str, object]] = []
        for finding in findings:
            if finding.code not in rules:
                rules[finding.code] = {
                    "id": finding.code,
                    "shortDescription": {"text": finding.code},
                    "help": {"text": finding.message},
                }
            level = "error"
            if finding.severity.lower() == "warning":
                level = "warning"
            elif finding.severity.lower() not in {"error", "warning"}:
                level = "note"
            results.append(
                {
                    "ruleId": finding.code,
                    "level": level,
                    "message": {"text": f"[{finding.skill_name}] {finding.message}"},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": finding.path},
                                "region": {"startLine": max(1, finding.line)},
                            }
                        }
                    ],
                }
            )
        payload = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "SKILLCHECK",
                            "informationUri": "https://github.com/jlov7/SKILLCHECK",
                            "rules": [rules[key] for key in sorted(rules.keys())],
                        }
                    },
                    "results": results,
                }
            ],
        }
        sarif_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return sarif_path

    def _summarize(self, rows: List[ReportRow]) -> ReportSummary:
        pass_count = sum(1 for row in rows if row.status == "pass")
        fail_count = sum(1 for row in rows if row.status != "pass")
        trust_scores = [row.trust_score for row in rows]
        avg_trust_score = round(sum(trust_scores) / len(trust_scores), 2) if trust_scores else 0.0
        min_trust_score = round(min(trust_scores), 2) if trust_scores else 0.0
        return ReportSummary(
            total=len(rows),
            pass_count=pass_count,
            fail_count=fail_count,
            avg_trust_score=avg_trust_score,
            min_trust_score=min_trust_score,
        )

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

    def write(self, *, write_sarif: bool = False) -> ReportResult:
        lint = self._load_json_files(".lint")
        probe = self._load_json_files(".probe")
        attest = self._load_json_files(".attestation")
        rows = self._collect_rows(lint, probe, attest)
        findings = self._collect_findings(lint, probe)
        summary = self._summarize(rows)
        csv_path = self._write_csv(rows)
        chart_path = self._write_chart(rows)
        md_path = self._write_markdown(rows, chart_path, summary)
        json_path = self._write_json(rows, summary)
        sarif_path = self._write_sarif(findings) if write_sarif else None
        return ReportResult(
            rows=rows,
            findings=findings,
            summary=summary,
            csv_path=csv_path,
            md_path=md_path,
            chart_path=chart_path,
            json_path=json_path,
            sarif_path=sarif_path,
        )
