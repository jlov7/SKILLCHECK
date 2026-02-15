# SKILLCHECK (research preview)

SKILLCHECK is a safety-first auditor for [Agent Skills][agentskills-spec]. Aligned with the open specification and the [skills-ref][skills-ref] reference validator, it gives platform, RAI, and engineering teams a repeatable way to examine any Skill bundle (folder or `.zip`) *before* toggling it on. This repository is personal R&D, not a product or funded roadmap, and is shared “as is” for anyone experimenting with Skills.

- **One-click confidence** – Run a single CLI command to lint, probe, and attest a Skill.
- **Actionable evidence** – Human-friendly Markdown reports, automation-ready JSON, and signed attestations.
- **No surprises** – Default-deny policies, offline operation, and optional sandbox execution keep audits contained.

> **Status:** Research preview (Apache-2.0). Synthetic sample Skills are provided for safe experimentation.
>
> **Independent research notice:** This repository is a personal passion project created in an individual capacity. It is not affiliated with, endorsed by, or representative of my employer, and all views and implementation choices here are my own.

---

## Table of contents
- [Who should read this](#who-should-read-this)
- [Quickstart](#quickstart)
- [What happens during an audit](#what-happens-during-an-audit)
- [Reading the outputs](#reading-the-outputs)
- [How SKILLCHECK keeps you safe](#how-skillcheck-keeps-you-safe)
- [Safety check matrix](#safety-check-matrix)
- [CLI reference](#cli-reference)
- [CI integration](#ci-integration)
- [FAQ](#faq)
- [Policies & customization](#policies--customization)
- [Advanced topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)
- [Docs & walkthroughs](#docs--walkthroughs)
- [Contributing](#contributing)
- [License](#license)

---

## Who should read this

| Persona | What you’ll learn |
| --- | --- |
| **Non-technical reviewers** (RAI / Trust) | How to read the report and spot PASS vs FAIL in under 5 minutes. |
| **Engineers / CI owners** | How to run SKILLCHECK locally and wire it into automation. |
| **Security engineers** | How policies, sandboxing, and attestations preserve provenance. |

---

## Quickstart

### 1. Prerequisites
- Python 3.10+
- macOS, Linux, or WSL (no external services needed)

### 2. Install
```bash
git clone https://github.com/jlov7/SKILLCHECK.git
cd SKILLCHECK
python -m pip install -e .[dev]
```

### 3. Run your first audit
```bash
# Lint + probe the safe sample Skill
python -m skillcheck.cli lint examples/brand-voice-editor
python -m skillcheck.cli probe examples/brand-voice-editor

# Aggregate results (fails if any Skill fails)
python -m skillcheck.cli report . --fail-on-failures
```

> Prefer shorter commands? Installing the project also registers a `skillcheck` console script (e.g. `skillcheck lint …`). Use whichever style fits your workflow.

### 4. Optional extras
- Audit zipped bundles: `python -m skillcheck.cli lint path/to/skill_bundle.zip`
- Exercise the sandbox: `SKILLCHECK_PROBE_EXEC=1 python -m skillcheck.cli probe <bundle> --exec`
- Generate SBOM + attestation: `python -m skillcheck.cli attest <bundle>`
- Print a quick PASS/FAIL table: `python -m skillcheck.cli report . --summary`
- Open a ready-made example: [`docs/sample-results.md`](docs/sample-results.md)
- Review golden demo artifacts: [`docs/artifacts/`](docs/artifacts)

> **Tip:** non-technical reviewers can open `.skillcheck/results.md`; automation can ingest `.skillcheck/results.json`.

---

## Local development

### Setup
```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

### Run (examples)
```bash
skillcheck lint examples/brand-voice-editor
skillcheck probe examples/brand-voice-editor
skillcheck report . --fail-on-failures
skillcheck fix . --base HEAD~1 --head HEAD --dry-run
```

### Test
```bash
ruff check .
mypy skillcheck
pytest -q
```

### Build/Release
```bash
python -m build
```

### Environment variables
| Variable | Purpose |
| --- | --- |
| `SKILLCHECK_PROBE_EXEC` | Set to `1`/`true` to force sandbox execution. |
| `SKILLCHECK_OTEL_EXPORTER` | Set to `console` or `otlp` to enable OpenTelemetry spans. |

For a quick CLI reference, run `skillcheck help` or see `docs/help.md`.

## What happens during an audit

```
┌──────────┐   lint      ┌──────────┐   probe     ┌────────────┐   attest    ┌───────────────┐
│ Skill(s) │────────────▶│ Static   │────────────▶│ Sandbox /  │────────────▶│ SBOM +         │
│ (folder/ │             │ lint     │             │ Heuristics │             │ Attestation    │
│   zip)   │             │ engine   │             │            │             │ generator      │
└──────────┘             └──────────┘             └────────────┘             └───────────────┘
          ╲__________________________________________ report __________________________________╱
                                   (Markdown / CSV / JSON + totals)
```

1. **Lint** inspects the Skill text: Agent Skills schema rules, secret sniffing, forbidden patterns, path traversal, file references, dependency allowlists, and allowed-tool policy checks.
2. **Probe** scans files for risky code patterns (Python/JS/shell) and (optionally) executes Python scripts inside a sandbox that blocks egress and writes.
3. **Attest** hashes every file, generates an SPDX-style SBOM, and records the policy & results in an attestation manifest.
4. **Report** aggregates everything so reviewers and CI pipelines can make a go/no-go decision quickly.

---

## Reading the outputs

| File | What it tells you | How to use it |
| --- | --- | --- |
| `.skillcheck/results.md` | Plain-language table with PASS/FAIL per Skill. | Share in reviews or PRs; no code knowledge needed. |
| `.skillcheck/results.json` | Same data with totals for automation. | Use in CI gating or dashboards. |
| `.skillcheck/<skill>.probe.json` | Detailed probe findings (e.g., blocked egress). | Escalate findings using the [remediation guide](docs/finding-remediation.md). |
| `.skillcheck/<skill>.attestation.json` | Provenance record (policy hash, digests, waivers). | Archive for audits or compliance. |

PASS = zero lint violations *and* zero probe violations. Any `EGRESS_*`, `WRITE_*`, or `forbidden_pattern_*` entry turns the row into a FAIL.

Need a visual? See [`docs/sample-results.md`](docs/sample-results.md).

---

## How SKILLCHECK keeps you safe

1. **Policy-driven lint** (`skillcheck/policies/default.policy.yaml`)
   - Enforces Agent Skills schema limits (name/description/compatibility) and naming rules.
   - Flags secrets, unsafe shell usage, path traversal, unapproved dependencies, and custom forbidden patterns.
   - Validates `allowed-tools` when a policy allowlist is configured.
   - Supports waivers with justification for rare exceptions.
2. **Dynamic probe**
   - Scans scripts for egress/write patterns in common languages (Python, JS, shell).
   - Optional sandbox execution blocks unauthorized sockets, subprocesses, and writes in real time (supported on macOS & Linux; Windows currently uses static probing unless you supply a sandbox).
   - Captures `EGRESS_SANDBOX`/`WRITE_SANDBOX` findings for accountability.
3. **SBOM + attestation**
   - Produces SPDX-style `sbom.json` with SHA-256 digests.
   - Generates attestation JSON citing policy hash, lint/probe summaries, and optional Sigstore signature.
4. **Telemetry (opt-in)**
   - With `opentelemetry-sdk` and `SKILLCHECK_OTEL_EXPORTER` set, emits spans using [GenAI & Agent semantic conventions][otel-ai] (still evolving—pin the version of the spec you target).
   - Architecture choices mirror Agent Skills guidance around progressive disclosure and provenance.

---

## Safety check matrix

| Stage | Threat addressed | Typical findings | Evidence written |
| --- | --- | --- | --- |
| Lint | Prompt injection, secrets, unsafe shell commands | `forbidden_pattern_2 (curl http)`, `SECRET_SUSPECT`, `PATH_TRAVERSAL`, `DEPENDENCY_PYPI`, `REFERENCE_MISSING`, `FRONTMATTER_ALLOWED_TOOLS` | `<skill>.lint.json` |
| Probe | Hidden runtime egress or writes | `EGRESS_SANDBOX`, `WRITE_SANDBOX`, blocked sockets | `<skill>.probe.json` |
| SBOM | Hidden payloads, mutable files | SHA-256 digests for every file | `<skill>.sbom.json` |
| Attestation | Provenance, policy adherence | Policy hash, waivers, optional signature | `<skill>.attestation.json` |
| Report | Governance, release gating | PASS/FAIL totals, charts | `results.csv`, `results.md`, `results.json`, `results_chart.png` |

For remediation tips, consult [`docs/finding-remediation.md`](docs/finding-remediation.md).

---

## CLI reference

| Command | Purpose | Useful flags |
| --- | --- | --- |
| `skillcheck lint <path>` | Static analysis (schema, secrets, forbidden patterns, dependencies). | `--policy`, `--policy-pack`, `--policy-version`. |
| `skillcheck probe <path>` | Dynamic heuristics + optional sandbox execution. | `--exec`, `--policy-pack`, `--policy-version`. |
| `skillcheck attest <path>` | Runs lint + probe and emits SBOM + attestation. | Install `[attest]` extras to enable Sigstore signing. |
| `skillcheck report <run-dir>` | Aggregates previous runs into CSV/MD/JSON (+ optional SARIF). | `--sarif`, `--github-annotations`, `--release-gate`, `--min-trust-score`, `--fail-on-low-trust`. |
| `skillcheck diff <repo-root>` | Audits only Skills touched between two git refs. | `--base`, `--head`, `--exec`, `--fail-on-failures`. |
| `skillcheck fix <repo-root>` | Plans or applies safe remediations for changed Skills, with optional commit/push/PR automation. | `--dry-run`, `--apply`, `--base`, `--head`, `--commit`, `--push`, `--pr`, `--branch-name`. |
| `skillcheck remediate <code>` | Prints guided fixes for a finding code. | `EGRESS_*`, `WRITE_*`, `SECRET_SUSPECT`, etc. |

All commands accept either directories or `.zip` bundles containing `SKILL.md` (or `skill.md`).

---

## Autonomous remediation flow

`skillcheck fix` is a deterministic, safety-first auto-remediation command.

```bash
# Preview safe fixes only (default)
skillcheck fix . --base origin/master --head HEAD --dry-run

# Apply safe fixes + open a PR
skillcheck fix . --base origin/master --head HEAD \
  --apply --commit --push --pr \
  --branch-name skillcheck-autofix
```

What it does:
- Scopes work to Skills touched between `--base` and `--head`.
- Applies safe frontmatter/schema fixes only (no script rewrites).
- Runs pre/post lint+probe and records trust delta.
- Writes `.skillcheck/fix/fix.results.json` with actions, scores, and git/PR metadata.

Guardrails:
- `--pr` requires `--push`.
- `--push` requires `--commit`.
- `--commit` requires `--apply`.

---

## CI integration

Example workflow (see repo’s `.github/workflows/skillcheck.yml`):

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
        python -m skillcheck.cli report . --fail-on-failures --sarif --release-gate standard
    - uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: .skillcheck/results.sarif
    - uses: actions/upload-artifact@v4
      with:
        name: skillcheck-artifacts
        path: .skillcheck/*
```

Add the workflow as a required status check to block merges until Skills pass. Consider posting `.skillcheck/results.md` as a PR comment or ingesting `results.json` into dashboards.

For CI best practices, see [`docs/engineer-walkthrough.md`](docs/engineer-walkthrough.md).

---

## FAQ

- **What if a Skill legitimately needs network access?** Add the destination to `allow.network.hosts` or document a waiver. The attestation records every waiver.
- **Probe says files aren’t readable.** Update `allow.filesystem.read_globs` to cover your resource directories (e.g., `resources/**`).
- **Can I run SKILLCHECK offline?** Yes. Everything runs locally. Sigstore will fall back to an unsigned attestation if it cannot reach the service.
- **Do I have to enable sandbox execution?** No. Static probing runs by default. Enable `--exec` when you want runtime assurance against hidden egress or writes.
- **Where do `.zip` bundles go?** They’re unpacked into a temporary directory and removed after the run. The attestation records the original location.

---

## Policies & customization

- Policy packs are built-in: `strict`, `balanced` (default), `research`, and `enterprise`.
- Pin expected policy versions with `--policy-version` in CI to prevent silent drift.
- Default policy (`skillcheck/policies/default.policy.yaml`) denies egress and restricts writes to `scratch/**`.
- Customize policies with snippets from the [Policy Cookbook](docs/policy-cookbook.md).
- Keep policies in source control and layer environment overrides via `--policy`.
- Documents waivers with justification; they appear in attestation outputs.

---

## Advanced topics

- **Sandbox execution** – Force via policy (`probe.enable_exec: true`) or CLI `--exec` flag.
- **Result artifacts** – `results.csv` (spreadsheets), `results.md` (humans), `results.json` (automation), `results_chart.png` (requires `matplotlib`).
- **Telemetry exporters** – Set `SKILLCHECK_OTEL_EXPORTER=console` for local spans, or `=otlp` to send to an OTLP endpoint (requires exporter package).
- **Custom artifact locations** – Use `skillcheck report --artifacts <dir>` to aggregate outputs from other directories.
- **Policy inheritance** – Combine base + environment policies to avoid drift.

---

## Troubleshooting

| Symptom | Quick fix |
| --- | --- |
| `ModuleNotFoundError: skillcheck` | Re-run `python -m pip install -e .[dev]` from repo root. |
| `skillcheck report` exits 1 | A Skill failed lint/probe; open `.skillcheck/results.md` or rerun without `--fail-on-failures`. |
| `skillcheck fix --pr` fails with “GitHub CLI \`gh\` is required” | Install GitHub CLI and authenticate (`gh auth login`) before using `--pr`. |
| `skillcheck fix` says no changed Skills | Verify `--base/--head` refs; check `.skillcheck/fix/fix.results.json` for scoped summary. |
| Sandbox says “write to ../foo escapes skill root” | Update scripts to write to allowlisted paths (default `scratch/**`) or adjust policy globs. |
| No telemetry spans appear | Ensure `SKILLCHECK_OTEL_EXPORTER` is set to `console` or `otlp`; otherwise spans are suppressed. |
| CI artifacts missing | Confirm `.skillcheck/*` uploads and earlier steps succeeded. |

See also: [Reviewer walkthrough](docs/reviewer-walkthrough.md) and [Engineer walkthrough](docs/engineer-walkthrough.md).

---

## Docs & walkthroughs
- [Sample report](docs/sample-results.md)
- [Policy cookbook](docs/policy-cookbook.md)
- [Finding remediation guide](docs/finding-remediation.md)
- [Reviewer walkthrough](docs/reviewer-walkthrough.md)
- [Engineer walkthrough](docs/engineer-walkthrough.md)
- [Security policy](SECURITY.md)

---

## Contributing

1. Fork and clone the repo.
2. Run `pytest -q` and `python -m skillcheck.cli report . --fail-on-failures` before opening a PR.
3. When adding rules or probes, include safe + risky sample Skills for reviewers.

Issues tagged “good first issue” welcome contributions for lint rules, sample Skills, and exporters.

---

## License

Apache-2.0. See [LICENSE](LICENSE).

---

[agentskills-spec]: https://agentskills.io/specification
[skills-ref]: https://github.com/agentskills/agentskills/tree/main/skills-ref
[otel-ai]: https://opentelemetry.io/docs/specs/semconv/gen-ai
