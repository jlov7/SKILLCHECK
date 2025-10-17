---
name: "Risky Net Egress Demo"
description: "Demonstrates bad patterns: attempts network egress and writes outside allowed paths; meant to fail SKILLCHECK."
version: "0.1.0"
---

# WARNING — Intentionally Risky (for testing)
This Skill is **designed to fail** policy checks and sandbox probes.

## Risky behaviors (should be flagged)
- Calls a shell script with `curl` to an external host.
- Runs a Python helper that opens a remote URL and writes **outside** the allowed `scratch/` dir.

## Files
- `scripts/unsafe_shell.sh` — uses `curl http://example.com` (forbidden by default).
- `scripts/do_egress.py` — uses `urllib.request.urlopen("https://example.com")` and writes `../outside.txt` (forbidden).

## How Claude might try (do not allow)
If code execution were enabled, it might invoke:
```bash
bash scripts/unsafe_shell.sh
python scripts/do_egress.py
```

This repository’s default policy **denies** both network egress and writes beyond `scratch/**`.
SKILLCHECK should:

1. Lint-flag forbidden patterns (`curl http`, `urllib.request`).
2. Probe-detect attempted egress and write outside allowlist.

```
