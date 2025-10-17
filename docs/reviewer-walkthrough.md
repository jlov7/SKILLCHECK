# Reviewer Walkthrough (Non-Technical)

Follow these steps to review a Skill audit without touching the terminal.

1. **Receive artifacts** (e.g., from CI or an engineer): look for `.skillcheck/` folder.
2. **Open `.skillcheck/results.md`** in your browser or any Markdown viewer.
   - Green “PASS” rows require no action.
   - Red “FAIL” rows need attention—note the Skill name and issue counts.
3. **If a row failed**, scroll to the row’s `Lint Violations` and `Egress/Write` columns to understand the type of problem.
4. **Check `.skillcheck/<skill>.probe.json`** for more detail on blocked egress or writes.
5. **Confirm waivers** (if any) in `.skillcheck/<skill>.attestation.json` under `policy.waivers`.
6. **Decision**:
   - ✅ Approve if all Skills are PASS.
   - ❌ If a Skill FAILS, send the finding code(s) to the engineer (use the [remediation guide](finding-remediation.md)).
7. **Archive evidence** by storing the attestation JSON (if required by policy).

That’s it—no command line required.

