# Autonomous Remediation PR Bot Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `skillcheck fix --pr` that audits changed skills, auto-applies safe remediations, verifies improvements, and can open a remediation PR.

**Architecture:** Add a deterministic remediation engine (`skillcheck/fixer.py`) that consumes lint findings and skill metadata, performs safe edits only, and emits a machine-readable remediation summary. Add CLI orchestration in `skillcheck/cli.py` to run changed-skill discovery, pre/post audits, trust delta computation, optional git branch/commit/push/PR operations, and summary artifacts.

**Tech Stack:** Python 3.10+, Typer CLI, existing lint/probe/report modules, Git CLI + GitHub CLI (`gh`), pytest/ruff/mypy.

---

## Scope Contract
- In scope:
  - `skillcheck fix` command and `--pr` flow.
  - Deterministic safe auto-fixes for schema/frontmatter issues only.
  - Pre/post verification reports and trust delta.
  - Optional branch/commit/push/PR operations with strict safety checks.
  - End-to-end tests for core happy path + guarded failure path.
- Out of scope:
  - Risky code rewrites in scripts (egress/write logic transformations).
  - Heuristic AI-generated patches.
  - Cross-repo orchestration.

## Safety Rules For Auto-Fixes
- Only rewrite `SKILL.md`/`skill.md`.
- Never mutate script source code.
- Never rename directories automatically.
- Never apply a fix when parser confidence is low; record as `skipped` with reason.

## Exhaustive TODO Checklist

### Phase 0: Tracking + Baseline
- [x] Create `.codex/SCRATCHPAD.md` with live execution state.
- [x] Add this feature plan document.
- [x] Capture baseline command outputs (`ruff`, `mypy`, `pytest`, `build`).

### Phase 1: Remediation Engine (TDD)
- [x] Add failing tests for safe fix behaviors in new `tests/test_fixer.py`.
- [x] Implement `skillcheck/fixer.py` datamodels and safe fix pipeline.
- [x] Handle missing `SKILL.md` by generating valid minimal file.
- [x] Normalize/fix frontmatter name/description/compatibility/unknown-field issues.
- [x] Emit remediation summary with `applied`, `skipped`, `errors` and edited files.
- [x] Run targeted tests and iterate to green.

### Phase 2: CLI `fix` Command (TDD)
- [x] Add failing CLI tests for `skillcheck fix` happy path and no-op path.
- [x] Add `fix` command with `--base/--head` changed-skill scope.
- [x] Add pre-fix and post-fix audits + trust delta summary.
- [x] Write remediation artifact JSON (`.skillcheck/fix/fix.results.json`).
- [x] Add `--dry-run` and `--apply` explicit mode guard.
- [x] Run targeted tests and iterate to green.

### Phase 3: Git/PR Automation (TDD)
- [x] Add failing tests for git orchestration guards (no changes, missing gh, etc.).
- [x] Implement optional branch/commit/push/PR flow flags:
  - [x] `--branch-name`
  - [x] `--commit`
  - [x] `--push`
  - [x] `--pr`
- [x] Enforce flag dependency (`--pr` requires `--push`, `--push` requires `--commit`).
- [x] Add deterministic commit/PR message templates.
- [x] Record PR URL in remediation artifact when created.
- [x] Run targeted tests and iterate to green.

### Phase 4: Docs + CI + Final Hardening
- [x] Document `fix` flow in `README.md` and `docs/help.md`.
- [x] Add troubleshooting guidance for skipped fixes and PR failures.
- [x] Update `AGENTS.md` command examples with `fix` usage.
- [x] Ensure CI still passes without requiring `gh` for unit tests.

### Phase 5: Full Verification + Release
- [x] Run full gate: `ruff`, `mypy`, `pytest`, `python -m build`.
- [x] Capture final outcomes in `.codex/SCRATCHPAD.md`.
- [x] Commit in reviewable chunks with conventional commit messages.
- [x] Push to `origin/master`.
- [x] Report completion with commands and artifact locations.

## Test Plan
- Unit tests:
  - `tests/test_fixer.py` for deterministic file mutations and skipped cases.
- CLI tests:
  - `tests/test_cli.py` for `fix --dry-run`, `fix --apply`, flag validation, and artifact output.
- Integration checks:
  - Use temporary git repo fixture to simulate changed-skill PR scenario.

## Risks
- YAML frontmatter rewrite may alter formatting unexpectedly.
- Git/PR automation can fail across environments if CLI tooling is unavailable.
- Over-fixing can introduce behavioral regressions if guardrails are weak.

## Mitigations
- Preserve markdown body verbatim; rewrite only normalized frontmatter.
- Make all mutation explicit (`--apply` required) and default to dry-run.
- Add precise tests for before/after content and no-op safety.

## Progress Log
- 2026-02-15: Plan initialized.
- 2026-02-15: Implemented remediation engine and `fix` CLI orchestration with guardrails and artifact output.
- 2026-02-15: Completed docs/help/walkthrough updates and added missing-tool UX for `git`/`gh`.
- 2026-02-15: Full quality gate passed (`ruff`, `mypy`, `pytest`, `python -m build`).
- 2026-02-15: Released to `origin/master` via commits `964def5` and `9d010de`.
