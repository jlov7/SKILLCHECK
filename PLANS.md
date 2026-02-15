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
