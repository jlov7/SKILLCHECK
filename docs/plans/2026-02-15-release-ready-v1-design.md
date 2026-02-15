# Release-ready v1 Design

## Goal
Make SKILLCHECK production/release-ready for a v1 launch with coherent CLI journeys, onboarding/help, verified quality gates, and complete docs.

## Primary Users
- **Engineers/CI owners** running audits and gating releases.
- **Reviewers/RAI** consuming Markdown results without touching the CLI.

## User Journeys
**Happy path:** install → lint → probe → report → share results. CLI output should always show the next step and where artifacts live. 
**Failure path:** missing `SKILL.md`, no artifacts to report, policy violations. Each should include a short cause + concrete next step.

## Onboarding & Help
- **First-run onboarding:** invoking `skillcheck` with no args shows a short welcome, quickstart, and next-step hints.
- **Empty states:** `report` with no artifacts prints a clear explanation and how to generate artifacts.
- **Progressive disclosure:** concise summary by default, with optional deeper guidance via `help` and docs.
- **In-app help:** a `skillcheck help` command prints a compact reference and points to `docs/help.md`.

## Accessibility & UX
- Avoid color-only status indicators; always include explicit PASS/FAIL text.
- Keep output short and scannable; route detail to JSON/MD artifacts.
- Ensure error messages are actionable and do not leak system paths unless needed.

## Quality Gates & CI
- Minimum gates: `ruff`, `mypy`, `pytest`, and `python -m build`.
- CI should run the above plus sample lint/probe as a smoke test.
- Add tests for first-run, help, and empty-state output.

## Security & Performance
- Preserve default-deny posture in policies; keep sandbox execution opt-in.
- Avoid unnecessary filesystem scans in CLI paths.
- Confirm no secrets committed and no unsafe defaults introduced.

## Docs
- Add `docs/help.md` as the minimal help page.
- Expand README with local setup/run/test/deploy/env vars sections.
- Keep walkthroughs aligned to the revised CLI output.
