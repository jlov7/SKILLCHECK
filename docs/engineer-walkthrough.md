# Engineer Walkthrough (Automation & CI)

This guide shows how to integrate SKILLCHECK into developer workflows and CI pipelines.

## Local workflow

1. Install once per repo: `python -m pip install -e .[dev]`.
2. Audit a Skill folder or zip:
   ```bash
   python -m skillcheck.cli lint path/to/skill --policy-pack balanced --policy-version 2
   python -m skillcheck.cli probe path/to/skill --exec --policy-pack balanced --policy-version 2  # optional but recommended
   python -m skillcheck.cli report . --fail-on-failures --sarif --release-gate standard
   ```
3. Inspect `.skillcheck/results.*` for status and share with reviewers.
4. For PR diffs only, run: `python -m skillcheck.cli diff . --base origin/master --head HEAD`.
5. To auto-remediate safe frontmatter/schema issues in changed Skills:
   ```bash
   python -m skillcheck.cli fix . --base origin/master --head HEAD --dry-run
   python -m skillcheck.cli fix . --base origin/master --head HEAD --apply --commit --push --pr --branch-name skillcheck-autofix
   ```

## Adding to CI

Example GitHub Actions stage:

```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - run: |
        python -m pip install -e .[dev]
        python -m skillcheck.cli lint skills/customer_support --policy-pack strict --policy-version 2
        python -m skillcheck.cli probe skills/customer_support --exec --policy-pack strict --policy-version 2
        python -m skillcheck.cli report . --fail-on-failures --sarif --release-gate strict
    - uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: .skillcheck/results.sarif
    - uses: actions/upload-artifact@v4
      with:
        name: skillcheck-artifacts
        path: .skillcheck/*
```

Key flags:
- `--fail-on-failures` ensures the build fails if any Skill violates policy.
- `--release-gate standard|strict` adds trust-score thresholds on top of pass/fail checks.
- `--policy-pack` and `--policy-version` lock governance behavior across environments.
- `--artifacts <dir>` lets you store outputs outside the repo root (useful in multi-step pipelines).
- `--policy` points to environment-specific policies (e.g., staging vs production).
- `fix --dry-run/--apply` helps teams auto-clean safe schema/frontmatter issues before review.
- `fix --pr` requires GitHub CLI (`gh`) and enforces `--pr -> --push -> --commit -> --apply`.

## Branch protections

1. Create a dedicated workflow (e.g., `.github/workflows/skillcheck.yml`).
2. Add the workflow as a required status check in GitHub.
3. Optional: Post-process `results.json` to add PR comments or dashboard entries.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `SKILLCHECK_PROBE_EXEC` | Set to `1`/`true` to force sandbox execution. |
| `SKILLCHECK_OTEL_EXPORTER` | Set to `console` or `otlp` to enable OpenTelemetry spans. |

## Tips

- Cache virtual environments in CI to speed up repeated runs.
- Keep `docs/policy-cookbook.md` nearby to adjust policies per environment.
- Use `--summary` (see CLI section) for quick terminal overviews during local runs.
