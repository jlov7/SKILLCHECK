# Demo Playbook (10 Minutes)

Use this script for live demos, recorded walkthroughs, and stakeholder briefings.

## 0. Setup (1 minute)

```bash
./scripts/demo.sh
```

If you are presenting live, keep one terminal running and one window open to `.skillcheck/demo/results.md`.

## 1. Framing (1 minute)

Say:
- "This is a pre-enable safety gate for Agent Skills."
- "It produces one truth source for engineering, security, and governance."

## 2. Safe baseline (2 minutes)

Show `brand-voice-editor` passing lint and probe.

Key line to emphasize:
- "No violations, no blocked runtime behaviors, ready for governance review."

## 3. Risk detection (2 minutes)

Show `risky-net-egress` failing checks.

Key line to emphasize:
- "We catch egress and unsafe behavior before this Skill is enabled."

## 4. Decision surface (2 minutes)

Open `.skillcheck/demo/results.md` and show:
- PASS/FAIL rows.
- Violation counts.
- One-file summary for non-technical reviewers.

## 5. Remediation guidance (1 minute)

Run:

```bash
skillcheck remediate EGRESS_SANDBOX
```

Key line to emphasize:
- "The tool is not just detection. It gives operators concrete next actions."

## 6. Close (1 minute)

Say:
- "This can run locally, in CI, and as a release gate."
- "Outputs are machine-readable and reviewer-friendly."
- "The same workflow scales from individual teams to enterprise governance."

## Backup artifacts (if live demo fails)

- `docs/artifacts/results.md`
- `docs/sample-results.md`
- `docs/technical-overview.md`
