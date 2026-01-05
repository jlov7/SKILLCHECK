#!/usr/bin/env bash
# Intentionally risky: raw curl to an external host (forbidden by default policy).
set -euo pipefail
curl http://example.com -s -o /dev/null
echo "[curl] attempted HTTP request to example.com"
