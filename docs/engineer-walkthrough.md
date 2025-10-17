# Engineer Walkthrough (Automation & CI)

This guide shows how to integrate SKILLCHECK into developer workflows and CI pipelines.

## Local workflow

1. Install once per repo: `python -m pip install -e .[dev]`.
2. Audit a Skill folder or zip:
   ```bash
   python -m skillcheck.cli lint path/to/skill
   python -m skillcheck.cli probe path/to/skill --exec  # optional but recommended
   python -m skillcheck.cli report . --fail-on-failures
   ```
3. Inspect `.skillcheck/results.*` for status and share with reviewers.

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
        python -m skillcheck.cli lint skills/customer_support
        python -m skillcheck.cli probe skills/customer_support --exec
        python -m skillcheck.cli report . --fail-on-failures
    - uses: actions/upload-artifact@v4
      with:
        name: skillcheck-artifacts
        path: .skillcheck/*
```

Key flags:
- `--fail-on-failures` ensures the build fails if any Skill violates policy.
- `--artifacts <dir>` lets you store outputs outside the repo root (useful in multi-step pipelines).
- `--policy` points to environment-specific policies (e.g., staging vs production).

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

