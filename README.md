# SKILLCHECK

SKILLCHECK is a safety-first auditor for [Claude Skills][anthropic-skills]. It gives platform, RAI, and engineering teams a repeatable way to examine any Skill bundle (folder or `.zip`) *before* toggling it on.

- **One-click confidence** – Run a single CLI command to lint, probe, and attest a Skill.
- **Actionable evidence** – Human-friendly Markdown reports, automation-ready JSON, and signed attestations.
- **No surprises** – Default-deny policies, offline operation, and optional sandbox execution keep audits contained.

> **Status:** Research preview (Apache-2.0). Synthetic sample Skills are provided for safe experimentation.

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
git clone https://github.com/example/skillcheck.git
cd skillcheck
python -m pip install -e .[dev]
```

### 3. Run your first audit
```bash
# Lint + probe the safe sample Skill
python -m skillcheck.cli lint examples/safe_brand_guidelines
python -m skillcheck.cli probe examples/safe_brand_guidelines

# Aggregate results (fails if any Skill fails)
python -m skillcheck.cli report . --fail-on-failures
```

### 4. Optional extras
- Audit zipped bundles: `python -m skillcheck.cli lint path/to/skill_bundle.zip`
- Exercise the sandbox: `SKILLCHECK_PROBE_EXEC=1 python -m skillcheck.cli probe <bundle> --exec`
- Generate SBOM + attestation: `python -m skillcheck.cli attest <bundle>`
- Print a quick PASS/FAIL table: `python -m skillcheck.cli report . --summary`
- Open a ready-made example: [`docs/sample-results.md`](docs/sample-results.md)

> **Tip:** non-technical reviewers can open `.skillcheck/results.md`; automation can ingest `.skillcheck/results.json`.

---

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

1. **Lint** inspects the Skill text: metadata limits, secret sniffing, forbidden patterns, path traversal.
2. **Probe** scans files for risky code and (optionally) executes Python scripts inside a sandbox that blocks egress and writes.
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
   - Enforces metadata limits aligned with [Anthropic guidance][anthropic-prompts].
   - Flags secrets, shell escapes, path traversal, and custom forbidden patterns.
   - Supports waivers with justification for rare exceptions.
2. **Dynamic probe**
   - Scans scripts for egress/write patterns.
   - Optional sandbox execution blocks unauthorized sockets, subprocesses, and writes in real time.
   - Captures `EGRESS_SANDBOX`/`WRITE_SANDBOX` findings for accountability.
3. **SBOM + attestation**
   - Produces SPDX-style `sbom.json` with SHA-256 digests.
   - Generates attestation JSON citing policy hash, lint/probe summaries, and optional Sigstore signature.
4. **Telemetry (opt-in)**
   - With `opentelemetry-sdk` and `SKILLCHECK_OTEL_EXPORTER` set, emits spans using [GenAI semantic conventions][otel-ai].

---

## Safety check matrix

| Stage | Threat addressed | Typical findings | Evidence written |
| --- | --- | --- | --- |
| Lint | Prompt injection, secrets, unsafe shell commands | `forbidden_pattern_2 (curl http)`, `SECRET_SUSPECT`, `PATH_TRAVERSAL` | `<skill>.lint.json` |
| Probe | Hidden runtime egress or writes | `EGRESS_SANDBOX`, `WRITE_SANDBOX`, blocked sockets | `<skill>.probe.json` |
| SBOM | Hidden payloads, mutable files | SHA-256 digests for every file | `<skill>.sbom.json` |
| Attestation | Provenance, policy adherence | Policy hash, waivers, optional signature | `<skill>.attestation.json` |
| Report | Governance, release gating | PASS/FAIL totals, charts | `results.csv`, `results.md`, `results.json`, `results_chart.png` |

For remediation tips, consult [`docs/finding-remediation.md`](docs/finding-remediation.md).

---

## CLI reference

| Command | Purpose | Useful flags |
| --- | --- | --- |
| `skillcheck lint <path>` | Static analysis (schema, secrets, forbidden patterns). | `--policy` to supply a custom policy. |
| `skillcheck probe <path>` | Dynamic heuristics + optional sandbox execution. | `--exec` or `SKILLCHECK_PROBE_EXEC=1` to force sandboxing. |
| `skillcheck attest <path>` | Runs lint + probe and emits SBOM + attestation. | Install `[attest]` extras to enable Sigstore signing. |
| `skillcheck report <run-dir>` | Aggregates previous runs into CSV/MD/JSON. | `--fail-on-failures` to exit non-zero on FAIL; `--artifacts <dir>` to read from another folder; `--summary` for a quick terminal table. |

All commands accept either directories or `.zip` bundles containing `SKILL.md`.

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
        python -m skillcheck.cli report . --fail-on-failures
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

[anthropic-skills]: https://docs.anthropic.com/en/docs/skills/overview
[anthropic-prompts]: https://docs.anthropic.com/en/docs/build-with-claude/prompting
[otel-ai]: https://opentelemetry.io/docs/specs/semconv/gen-ai
