# AGENTS

Repo working agreements for SKILLCHECK.

## Commands
- Setup: `uv venv .venv` then `source .venv/bin/activate` then `uv pip install -e '.[dev]'`
- Lint: `ruff check .`
- Typecheck: `mypy skillcheck`
- Tests: `pytest -q`
- Build: `python -m build`
- Sample audit (happy path):
  - `./scripts/try.sh`
  - `./scripts/demo.sh`
  - `skillcheck lint examples/brand-voice-editor --policy-pack balanced --policy-version 2`
  - `skillcheck probe examples/brand-voice-editor --policy-pack balanced --policy-version 2`
  - `skillcheck report . --fail-on-failures --sarif --release-gate standard`
  - `skillcheck diff . --base HEAD~1 --head HEAD`
  - `skillcheck fix . --base HEAD~1 --head HEAD --dry-run`
  - `skillcheck remediate EGRESS_SANDBOX`

## Quality Bar
- Lint/typecheck/tests/build pass.
- CLI output is clear and actionable, with friendly failure guidance.
- Docs updated for any UX or behavior changes.
- SARIF output and release-gate behavior verified when report options change.
- No secrets or large binaries committed.
- Changes are small, reviewable, and aligned to the v1 checklist.
