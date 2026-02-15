# SKILLCHECK Help

## Quickstart
```bash
skillcheck lint <path-to-skill>
skillcheck probe <path-to-skill>
skillcheck report . --fail-on-failures
skillcheck diff . --base HEAD~1 --head HEAD
skillcheck remediate EGRESS_SANDBOX
```

Artifacts are written to `.skillcheck/` by default.

## Common Issues
- **Missing `SKILL.md`**: Your skill folder or zip must include `SKILL.md` (or `skill.md`) at its root.
- **No artifacts to report**: Run `lint` and `probe` before `report`.
- **Probe sandbox fails**: Use `--exec` only when you want sandbox execution; otherwise use static probing.

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
