# SKILLCHECK Help

## Quickstart
```bash
skillcheck lint <path-to-skill>
skillcheck probe <path-to-skill>
skillcheck report . --fail-on-failures
```

Artifacts are written to `.skillcheck/` by default.

## Common Issues
- **Missing `SKILL.md`**: Your skill folder or zip must include `SKILL.md` (or `skill.md`) at its root.
- **No artifacts to report**: Run `lint` and `probe` before `report`.
- **Probe sandbox fails**: Use `--exec` only when you want sandbox execution; otherwise use static probing.

## Tips
- Add custom policies with `--policy path/to/policy.yaml`.
- Use `--summary` on `report` for a condensed PASS/FAIL view.
- For non-technical reviews, share `.skillcheck/results.md`.

## Next Steps
- `docs/engineer-walkthrough.md`
- `docs/reviewer-walkthrough.md`
- `docs/policy-cookbook.md`
