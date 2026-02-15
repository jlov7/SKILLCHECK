# Release-ready v1 (ExecPlan)

## Purpose / Big Picture
Make SKILLCHECK release-ready for a v1 launch by ensuring coherent end-to-end journeys, onboarding/help, quality gates, accessibility/performance basics, security hygiene, and complete docs.

## Approach
Ship in small, reviewable milestones. Start with steering docs and a concrete v1 design, then improve CLI onboarding/help and failure UX with tests, then finish docs + CI quality gates and verify all checks.

## Progress
- [x] Milestone 1: Steering docs + v1 design
- [x] Milestone 2: CLI onboarding/help UX + tests
- [x] Milestone 3: Docs/CI quality gates + release verification

## Milestone 1: Steering Docs + v1 Design
- [x] Add `AGENTS.md` working agreements and commands
- [x] Add `RELEASE_CHECKLIST.md` with v1 definition of done
- [x] Add `QUESTIONS.md` and log unknowns
- [x] Write v1 design in `docs/plans/2026-02-15-release-ready-v1-design.md`
- [x] Update this plan with milestones and risks
- [x] Run tests/lint/typecheck/build (quality gate)

## Milestone 2: CLI Onboarding/Help UX + Tests
- [x] Add first-run onboarding output for `skillcheck` with no args
- [x] Add in-app help command with short guidance + pointers
- [x] Improve empty-state messages (e.g., report with no artifacts)
- [x] Ensure failure copy is clear for missing SKILL.md/skill.md (existing message already explicit)
- [x] Add/adjust tests for CLI UX paths
- [x] Run tests/lint/typecheck/build (quality gate)

## Milestone 3: Docs/CI Quality Gates + Release Verification
- [x] Add minimal help doc page and link from README
- [x] Update README with local setup/run/test/deploy/env var notes
- [x] Ensure CI includes lint/typecheck/tests/build steps
- [x] Validate accessibility/performance/security basics
- [x] Final verification and release report
- [x] Run tests/lint/typecheck/build (quality gate)

## Risks
- CLI UX changes could subtly alter exit codes or output expectations.
- Adding build verification may require new tooling in CI and local docs.

## Validation Gates
- `ruff check .`
- `mypy skillcheck`
- `pytest -q`
- `python -m build`

## Surprises & Discoveries
- `python -m build` reported setuptools deprecation warnings for `project.license` table and license classifier usage; resolved by switching to SPDX string and removing deprecated classifier.

## Decision Log
- Adopt milestone-based delivery to keep changes small and reviewable.

## Outcomes & Retrospective
- Completed all three milestones with onboarding/help UX, docs, and CI/build gates.
- Added tests for key CLI onboarding and docs/packaging readiness.
- Build warnings resolved by updating license metadata.

---

# v1.1 Feature Pack (ExecPlan)

## Purpose / Big Picture
Ship the highest-impact post-v1 upgrades: changed-files audits, SARIF/PR integration, policy packs with version pinning, guided remediation, and trust-score release gates.

## Progress
- [x] Milestone 1: Changed-files `diff` audit command
- [x] Milestone 2: SARIF export + GitHub annotations
- [x] Milestone 3: Policy packs + version pinning
- [x] Milestone 4: Guided remediation + trust-score release gates
- [x] Milestone 5: Docs and CI sync

## Surprises & Discoveries
- CI workflow still referenced old branch/path names; corrected to keep checks green and reproducible.
- Policy YAML files needed explicit package-data config to ensure wheel artifacts include all packs.

## Decision Log
- Added release-gate presets (`standard`, `strict`) to keep gating simple while supporting custom thresholds.
- Kept `diff` output isolated in `.skillcheck/diff` by default to avoid mixing with full-run artifacts.

## Outcomes & Retrospective
- Added end-to-end automation support for PR-native governance via SARIF and annotation output.
- Added deterministic policy governance with pack selection and version pinning.
- Added remediation UX and trust-based release gates with CI-friendly non-zero exits.

---

# Autonomous Remediation PR Bot (ExecPlan)

## Purpose / Big Picture
Ship a high-complexity, production-safe remediation flow that can detect changed Skills, apply deterministic safe fixes, and optionally open a remediation PR with auditable artifacts.

## Progress
- [x] Milestone 1: Safe remediation engine with tests
- [x] Milestone 2: `skillcheck fix` command and artifact output
- [x] Milestone 3: Git/PR automation guardrails
- [x] Milestone 4: Docs/help/walkthrough updates
- [ ] Milestone 5: Final verification, commit, and push

## Surprises & Discoveries
- A no-op `fix` run still benefits from writing a zeroed `fix.results.json` artifact for traceability.
- `--pr` UX needed explicit handling when `gh` is unavailable to avoid raw stack traces.

## Decision Log
- Limited auto-remediation to frontmatter/schema edits only; no script rewrites for safety.
- Defaulted `fix` to dry-run to keep behavior non-destructive unless explicitly requested.

## Outcomes & Retrospective
- In progress.
