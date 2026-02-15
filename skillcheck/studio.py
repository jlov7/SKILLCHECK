"""Streamlit UI for SKILLCHECK Studio."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st

from .utils import slugify

st.set_page_config(
    page_title="SKILLCHECK Studio",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_styles() -> None:
    st.markdown(
        """
<style>
.block-container { max-width: 1200px; padding-top: 1.25rem; }
.hero {
  background: linear-gradient(135deg, #0f172a 0%, #1f2937 55%, #111827 100%);
  color: #f8fafc;
  padding: 1.1rem 1.3rem;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  margin-bottom: 0.8rem;
}
.hero h2 { margin: 0 0 0.35rem 0; font-size: 1.35rem; }
.hero p { margin: 0.2rem 0; color: #dbeafe; }
.card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.9rem;
}
.small-muted { color: #64748b; font-size: 0.9rem; }
</style>
        """,
        unsafe_allow_html=True,
    )


def _run_cmd(args: List[str]) -> Tuple[int, str]:
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    return result.returncode, output.strip()


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _status_badge(value: str) -> str:
    return "✅ PASS" if value.lower() == "pass" else "❌ FAIL"


def _render_hero(summary: Dict[str, Any]) -> None:
    st.markdown(
        """
<div class="hero">
  <h2>SKILLCHECK Studio</h2>
  <p>Guided audits for Agent Skills with clear reviewer outputs and demo-ready story flow.</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Skills", summary.get("total", 0))
    c2.metric("Pass", summary.get("pass_count", 0))
    c3.metric("Fail", summary.get("fail_count", 0))
    c4.metric("Avg trust", summary.get("avg_trust_score", 0.0))


def _artifact_paths(artifact_dir: str) -> Dict[str, Path]:
    base = Path(artifact_dir)
    return {
        "results_json": base / "results.json",
        "results_md": base / "results.md",
        "results_sarif": base / "results.sarif",
    }


def _init_state() -> None:
    defaults = {
        "skill_path": "examples/brand-voice-editor",
        "last_output": "",
        "last_status": "idle",
        "last_command": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _build_cmds(
    skill_path: str,
    artifact_dir: str,
    policy_pack: str,
    policy_version: int,
    enable_exec: bool,
) -> Dict[str, List[str]]:
    base_cmd = [sys.executable, "-m", "skillcheck.cli"]

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
    return {"lint": lint_cmd, "probe": probe_cmd, "report": report_cmd}


def _execute_action(label: str, cmd: List[str]) -> None:
    rc, out = _run_cmd(cmd)
    st.session_state["last_output"] = out or "(no output)"
    st.session_state["last_command"] = "$ " + " ".join(cmd)
    if rc == 0:
        st.session_state["last_status"] = "success"
        st.success(f"{label} completed successfully")
    else:
        st.session_state["last_status"] = "warning"
        st.warning(f"{label} exited with code {rc}. This may be expected for risky samples.")


def _render_onboarding() -> None:
    st.subheader("Onboarding")
    journey = st.radio(
        "Choose your journey",
        [
            "I want to evaluate a Skill quickly",
            "I want to run a live stakeholder demo",
            "I need to explain what this project does",
        ],
        horizontal=False,
    )

    if journey == "I want to evaluate a Skill quickly":
        st.markdown(
            """
1. Run `./scripts/try.sh`.
2. Open `.skillcheck/quickstart/results.md`.
3. Share PASS/FAIL summary with your reviewer.
            """
        )
    elif journey == "I want to run a live stakeholder demo":
        st.markdown(
            """
1. Run `./scripts/demo.sh`.
2. Keep this Studio tab open on **Results**.
3. Follow `docs/demo-playbook.md` for the 10-minute talk track.
            """
        )
    else:
        st.markdown(
            """
1. Start with `docs/why-skillcheck.md` for business narrative.
2. Use `docs/technical-overview.md` for architecture.
3. Share `docs/share-pack.md` for reusable messaging.
            """
        )

    c1, c2 = st.columns(2)
    if c1.button("Use safe sample", use_container_width=True):
        st.session_state["skill_path"] = "examples/brand-voice-editor"
        st.success("Skill path set to safe sample")
    if c2.button("Use risky sample", use_container_width=True):
        st.session_state["skill_path"] = "examples/risky-net-egress"
        st.success("Skill path set to risky sample")


def _render_runner(
    artifact_dir: str,
    policy_pack: str,
    policy_version: int,
    enable_exec: bool,
) -> None:
    st.subheader("Run Audit")
    st.text_input(
        "Skill path (folder or .zip)",
        key="skill_path",
        help="Example: examples/brand-voice-editor",
    )

    cmds = _build_cmds(st.session_state["skill_path"], artifact_dir, policy_pack, policy_version, enable_exec)

    c1, c2, c3 = st.columns(3)
    run_lint = c1.button("Run lint", use_container_width=True)
    run_probe = c2.button("Run probe", use_container_width=True)
    run_full = c3.button("Run full audit", type="primary", use_container_width=True)

    if run_lint:
        _execute_action("Lint", cmds["lint"])
    if run_probe:
        _execute_action("Probe", cmds["probe"])
    if run_full:
        rc_lint, out_lint = _run_cmd(cmds["lint"])
        rc_probe, out_probe = _run_cmd(cmds["probe"])
        rc_report, out_report = _run_cmd(cmds["report"])
        combined = "\n\n".join(
            [
                "$ " + " ".join(cmds["lint"]),
                out_lint,
                "$ " + " ".join(cmds["probe"]),
                out_probe,
                "$ " + " ".join(cmds["report"]),
                out_report,
            ]
        ).strip()
        st.session_state["last_command"] = "$ full audit sequence"
        st.session_state["last_output"] = combined
        if rc_lint == 0 and rc_probe == 0 and rc_report == 0:
            st.session_state["last_status"] = "success"
            st.success("Full audit completed successfully")
        else:
            st.session_state["last_status"] = "warning"
            st.warning("Full audit completed with findings or command failures (expected for risky samples).")

    if st.session_state["last_output"]:
        with st.expander("Latest command output", expanded=True):
            st.code(st.session_state["last_command"] + "\n\n" + st.session_state["last_output"], language="bash")


def _render_results(artifact_dir: str) -> None:
    st.subheader("Results")
    paths = _artifact_paths(artifact_dir)
    payload = _load_json(paths["results_json"])
    if not payload:
        st.info("No `results.json` found yet in this artifact directory. Run a full audit first.")
        return

    summary = payload.get("summary", {})
    rows = payload.get("rows", [])
    _render_hero(summary)

    view = st.radio("View", ["All skills", "Failed skills only"], horizontal=True)
    if view == "Failed skills only":
        rows = [row for row in rows if str(row.get("status", "")).lower() != "pass"]

    table_data = []
    for row in rows:
        table_data.append(
            {
                "Skill": row.get("skill_name", ""),
                "Status": _status_badge(str(row.get("status", "fail"))),
                "Trust": row.get("trust_score", 0),
                "Lint violations": row.get("lint_violations", 0),
                "Probe egress": row.get("probe_egress", 0),
                "Probe writes": row.get("probe_writes", 0),
            }
        )

    st.dataframe(table_data, use_container_width=True)

    if rows:
        selected_skill = st.selectbox("Inspect skill details", [r.get("skill_name", "") for r in rows], index=0)
        stem = slugify(selected_skill)
        lint_payload = _load_json(Path(artifact_dir) / f"{stem}.lint.json")
        probe_payload = _load_json(Path(artifact_dir) / f"{stem}.probe.json")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Lint findings**")
            issues = lint_payload.get("issues", []) if lint_payload else []
            if issues:
                st.dataframe(
                    [
                        {
                            "Severity": issue.get("severity", ""),
                            "Code": issue.get("code", ""),
                            "Path": issue.get("path", ""),
                            "Message": issue.get("message", ""),
                        }
                        for issue in issues
                    ],
                    use_container_width=True,
                )
            else:
                st.success("No lint issues")

        with c2:
            st.markdown("**Probe findings**")
            egress = probe_payload.get("egress_attempts", []) if probe_payload else []
            writes = probe_payload.get("disallowed_writes", []) if probe_payload else []
            combined = egress + writes
            if combined:
                st.dataframe(
                    [
                        {
                            "Code": item.get("code", ""),
                            "Evidence": item.get("message", ""),
                        }
                        for item in combined
                    ],
                    use_container_width=True,
                )
            else:
                st.success("No probe issues")

    with st.expander("Raw results.json"):
        st.json(payload)

    st.markdown(
        f"<div class='small-muted'>Artifacts: {artifact_dir}</div>",
        unsafe_allow_html=True,
    )


def _render_story() -> None:
    st.subheader("Storyline")
    st.markdown(
        """
### Executive narrative
1. Skills are high-leverage but can hide risky behavior.
2. SKILLCHECK provides a pre-enable confidence gate.
3. Teams get one report surface for both technical and non-technical decisions.

### Technical narrative
- **Lint** enforces policy and schema controls.
- **Probe** detects risky runtime behavior.
- **Report** provides CI-ready and reviewer-ready outputs.

### Demo close
- Safer enablement, faster review cycles, clearer governance evidence.
        """
    )


def _render_help() -> None:
    st.subheader("Guide & Help")
    with st.expander("How to run a first audit", expanded=True):
        st.markdown(
            """
- Click **Use safe sample** in Onboarding.
- Go to **Run Audit** and click **Run full audit**.
- Open **Results** to inspect PASS/FAIL and findings.
            """
        )
    with st.expander("How to run a live demo"):
        st.markdown(
            """
- Run `./scripts/demo.sh` in terminal.
- Keep Studio open to the **Results** tab.
- Follow `docs/demo-playbook.md` for timing and narrative.
            """
        )
    with st.expander("Where to get more details"):
        st.markdown(
            """
- `docs/help.md`
- `docs/technical-overview.md`
- `docs/why-skillcheck.md`
- `docs/share-pack.md`
            """
        )


_init_state()
_inject_styles()

with st.sidebar:
    st.header("Studio configuration")
    artifact_dir = st.text_input(
        "Artifact directory",
        value=".skillcheck/studio",
        help="Run-specific directory for lint/probe/report outputs.",
    )
    policy_pack = st.selectbox("Policy pack", ["balanced", "strict", "research", "enterprise"], index=0)
    policy_version = st.number_input("Policy version", min_value=1, max_value=99, value=2, step=1)
    enable_exec = st.toggle("Enable probe sandbox execution", value=False)

    st.markdown("---")
    st.markdown("**Quick links**")
    st.code("./scripts/try.sh", language="bash")
    st.code("./scripts/demo.sh", language="bash")
    st.code("skillcheck studio", language="bash")

results_payload = _load_json(_artifact_paths(artifact_dir)["results_json"])
summary_data = results_payload.get("summary", {}) if results_payload else {}
_render_hero(summary_data)

onboarding_tab, run_tab, results_tab, story_tab, help_tab = st.tabs(
    ["Onboarding", "Run Audit", "Results", "Storyline", "Help"]
)

with onboarding_tab:
    _render_onboarding()

with run_tab:
    _render_runner(artifact_dir, policy_pack, int(policy_version), enable_exec)

with results_tab:
    _render_results(artifact_dir)

with story_tab:
    _render_story()

with help_tab:
    _render_help()
