# SKILLCHECK Help

## Quickstart
```bash
skillcheck lint <path-to-skill>
skillcheck probe <path-to-skill>
skillcheck report . --fail-on-failures
skillcheck diff . --base HEAD~1 --head HEAD
skillcheck fix . --base HEAD~1 --head HEAD --dry-run
skillcheck remediate EGRESS_SANDBOX
```

Artifacts are written to `.skillcheck/` by default.
Use `--output-dir docs/artifacts` when you intentionally want committed demo outputs.

`fix` writes remediation artifacts to `.skillcheck/fix/fix.results.json` by default.

## `fix` command modes
- `--dry-run` (default): proposes safe remediations without mutating files.
- `--apply`: applies safe remediations to changed Skills.
- `--commit`: stages and commits changed Skill files (`--apply` required).
- `--push`: pushes the remediation branch (`--commit` required).
- `--pr`: opens a GitHub pull request (`--push` required, `gh` CLI required).

## Common Issues
- **Missing `SKILL.md`**: Your skill folder or zip must include `SKILL.md` (or `skill.md`) at its root.
- **No artifacts to report**: Run `lint` and `probe` before `report`.
- **Probe sandbox fails**: Use `--exec` only when you want sandbox execution; otherwise use static probing.
- **`fix --pr` fails**: Install and authenticate GitHub CLI (`gh auth login`) before enabling `--pr`.
- **`fix` found no changed Skills**: Check `--base`/`--head` refs and inspect `.skillcheck/fix/fix.results.json`.

## Tips
- Add custom policies with `--policy path/to/policy.yaml`.
- Use built-in policy packs with `--policy-pack strict|balanced|research|enterprise`.
- Pin policy versions in CI using `--policy-version 2`.
- Use `--summary` on `report` for a condensed PASS/FAIL view.
- Use `--sarif` and `--github-annotations` for PR-native review surfaces.
- Use `--release-gate standard|strict` for trust-score-based release gating.
- For non-technical reviews, share `.skillcheck/results.md`.

## Next Steps
- `docs/engineer-walkthrough.md`
- `docs/reviewer-walkthrough.md`
- `docs/policy-cookbook.md`
