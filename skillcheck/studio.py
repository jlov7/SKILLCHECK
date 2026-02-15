"""Streamlit UI for SKILLCHECK."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import streamlit as st


st.set_page_config(
    page_title="SKILLCHECK Studio",
    layout="wide",
)


def _run_cmd(args: List[str]) -> Tuple[int, str]:
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    return result.returncode, output.strip()


def _load_results(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _status_badge(value: str) -> str:
    return "PASS" if value.lower() == "pass" else "FAIL"


st.title("SKILLCHECK Studio")
st.caption("Run audits, review risk posture, and tell the story from one graphical interface.")

with st.sidebar:
    st.header("Run configuration")
    artifact_dir = st.text_input("Artifact directory", value=".skillcheck/studio")
    policy_pack = st.selectbox("Policy pack", ["balanced", "strict", "research", "enterprise"], index=0)
    policy_version = st.number_input("Policy version", min_value=1, max_value=99, value=2, step=1)
    enable_exec = st.toggle("Enable probe sandbox execution", value=False)

launch_tab, run_tab, results_tab, story_tab = st.tabs(["Launch", "Run Audit", "Results", "Story"])

with launch_tab:
    st.subheader("Start in minutes")
    st.markdown(
        """
- `./scripts/try.sh` for a complete first-run experience.
- `./scripts/demo.sh` for a polished live demo sequence.
- `docs/demo-playbook.md` for presenter talk track.
        """
    )
    st.info("Tip: point this UI to a dedicated artifact directory per demo to keep runs clean and comparable.")

with run_tab:
    st.subheader("Audit runner")
    skill_path = st.text_input("Skill path (folder or .zip)", value="examples/brand-voice-editor")
    col1, col2 = st.columns(2)
    run_lint = col1.button("Run lint")
    run_probe = col2.button("Run probe")
    run_full = st.button("Run lint + probe + summary report", type="primary")

    base_cmd = [sys.executable, "-m", "skillcheck.cli"]
    output_area = st.empty()

    def execute(action: str, cmd: List[str]) -> None:
        rc, out = _run_cmd(cmd)
        if rc == 0:
            st.success(f"{action} completed successfully")
        else:
            st.error(f"{action} exited with code {rc}")
        output_area.code(out or "(no output)", language="bash")

    lint_cmd = base_cmd + [
        "lint",
        skill_path,
        "--output-dir",
        artifact_dir,
        "--policy-pack",
        policy_pack,
        "--policy-version",
        str(policy_version),
    ]
    probe_cmd = base_cmd + [
        "probe",
        skill_path,
        "--output-dir",
        artifact_dir,
        "--policy-pack",
        policy_pack,
        "--policy-version",
        str(policy_version),
    ]
    if enable_exec:
        probe_cmd.append("--exec")

    report_cmd = base_cmd + [
        "report",
        ".",
        "--artifacts",
        artifact_dir,
        "--summary",
    ]

    if run_lint:
        execute("Lint", lint_cmd)
    if run_probe:
        execute("Probe", probe_cmd)
    if run_full:
        rc_lint, out_lint = _run_cmd(lint_cmd)
        rc_probe, out_probe = _run_cmd(probe_cmd)
        rc_report, out_report = _run_cmd(report_cmd)
        combined = "\n\n".join(
            [
                "$ " + " ".join(lint_cmd),
                out_lint,
                "$ " + " ".join(probe_cmd),
                out_probe,
                "$ " + " ".join(report_cmd),
                out_report,
            ]
        )
        if rc_lint == 0 and rc_probe == 0 and rc_report == 0:
            st.success("Full audit completed successfully")
        else:
            st.warning("Full audit completed with findings or command failures (expected for risky samples).")
        output_area.code(combined.strip(), language="bash")

with results_tab:
    st.subheader("Results explorer")
    results_path = Path(artifact_dir) / "results.json"
    payload = _load_results(results_path)
    if not payload:
        st.info("No results.json found yet. Run an audit first.")
    else:
        summary = payload.get("summary", {})
        rows = payload.get("rows", [])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", summary.get("total", 0))
        c2.metric("Pass", summary.get("pass_count", 0))
        c3.metric("Fail", summary.get("fail_count", 0))
        c4.metric("Avg trust", summary.get("avg_trust_score", 0.0))

        if rows:
            table_data = []
            for row in rows:
                table_data.append(
                    {
                        "Skill": row.get("skill_name", ""),
                        "Status": _status_badge(row.get("status", "fail")),
                        "Trust": row.get("trust_score", 0),
                        "Lint violations": row.get("lint_violations", 0),
                        "Probe egress": row.get("probe_egress", 0),
                        "Probe writes": row.get("probe_writes", 0),
                    }
                )
            st.dataframe(table_data, use_container_width=True)
        with st.expander("Raw results.json"):
            st.json(payload)

with story_tab:
    st.subheader("Narrative flow")
    st.markdown(
        """
1. **Problem**: Skills are powerful but can hide risky runtime behavior.
2. **What SKILLCHECK does**: lint + probe + attest + report.
3. **Decision surface**: one PASS/FAIL summary for technical and non-technical reviewers.
4. **Operational model**: run locally, in CI, and enforce release gates.
5. **Outcome**: faster enablement with stronger governance confidence.
        """
    )
    st.caption("For scripted delivery, use docs/demo-playbook.md and scripts/demo.sh.")
