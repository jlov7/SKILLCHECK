#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
ARTIFACT_DIR=".skillcheck/demo"

section() {
  printf '\n\n%s\n' "################################################################"
  printf '%s\n' "$1"
  printf '%s\n' "################################################################"
}

run() {
  printf '\n$ %s\n' "$*"
  "$@"
}

install_project() {
  if command -v uv >/dev/null 2>&1; then
    run uv pip install -e ".[dev]"
  else
    run python -m pip install --upgrade pip
    run python -m pip install -e ".[dev]"
  fi
}

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
mkdir -p "$ARTIFACT_DIR"
find "$ARTIFACT_DIR" -type f -delete

install_project

section "1) Baseline: safe Skill passes"
run skillcheck lint examples/brand-voice-editor --output-dir "$ARTIFACT_DIR" --policy-pack balanced --policy-version 2
run skillcheck probe examples/brand-voice-editor --output-dir "$ARTIFACT_DIR" --policy-pack balanced --policy-version 2

section "2) Risk demonstration: risky Skill fails"
set +e
skillcheck lint examples/risky-net-egress --output-dir "$ARTIFACT_DIR" --policy-pack balanced --policy-version 2
skillcheck probe examples/risky-net-egress --output-dir "$ARTIFACT_DIR" --policy-pack balanced --policy-version 2
set -e

section "3) Executive summary report"
run skillcheck report . --artifacts "$ARTIFACT_DIR" --summary --sarif

section "4) Guided remediation UX"
run skillcheck remediate EGRESS_SANDBOX

section "5) Artifact locations"
printf '%s\n' "- Summary report: $ARTIFACT_DIR/results.md"
printf '%s\n' "- Machine report: $ARTIFACT_DIR/results.json"
printf '%s\n' "- SARIF:          $ARTIFACT_DIR/results.sarif"
printf '%s\n' "- Demo narrative: docs/demo-playbook.md"
