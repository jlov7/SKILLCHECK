# AGENTS

Repo working agreements for SKILLCHECK.

## Commands
- Setup: `uv venv .venv` then `source .venv/bin/activate` then `uv pip install -e '.[dev]'`
- Lint: `ruff check .`
- Typecheck: `mypy skillcheck`
- Tests: `pytest -q`
- Build: `python -m build`
- Sample audit (happy path):
  - `skillcheck lint examples/brand-voice-editor`
  - `skillcheck probe examples/brand-voice-editor`
  - `skillcheck report . --fail-on-failures`

## Quality Bar
- Lint/typecheck/tests/build pass.
- CLI output is clear and actionable, with friendly failure guidance.
- Docs updated for any UX or behavior changes.
- No secrets or large binaries committed.
- Changes are small, reviewable, and aligned to the v1 checklist.
