# SKILLCHECK Launch Hub

SKILLCHECK helps teams evaluate Agent Skills before enablement using policy-driven checks, runtime probing, provenance artifacts, and governance-ready reporting.

## Start in under 5 minutes

```bash
./scripts/try.sh
```

You will get:
- A passing safe sample run.
- A failing risky sample run.
- A shareable markdown report at `.skillcheck/quickstart/results.md`.

## Choose your path

### Non-technical path
- Start: [Why SKILLCHECK exists](why-skillcheck.md)
- Review flow: [Reviewer walkthrough](reviewer-walkthrough.md)
- Demo script: [Demo playbook](demo-playbook.md)

### Technical path
- Start: [Engineer walkthrough](engineer-walkthrough.md)
- Deep dive: [Technical overview](technical-overview.md)
- Policy tuning: [Policy cookbook](policy-cookbook.md)
- Remediation mapping: [Finding remediation](finding-remediation.md)

## Live demo assets
- Scripted terminal demo: `./scripts/demo.sh`
- Graphical app demo: `python -m pip install -e .[ui] && skillcheck studio`
- Curated artifacts: [`docs/artifacts/`](artifacts)
- Sample narrative report: [Sample results](sample-results.md)

## How to share this quickly

1. Send the repo README for high-level context.
2. Send this hub page for guided navigation.
3. Run `./scripts/demo.sh` live or share recorded output with `docs/demo-playbook.md`.
