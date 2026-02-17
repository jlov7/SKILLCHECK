#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
ARTIFACT_DIR=".skillcheck/quickstart"

print_header() {
  printf '\n%s\n' "============================================================"
  printf '%s\n' "$1"
  printf '%s\n' "============================================================"
}

run_cmd() {
  printf '\n$ %s\n' "$*"
  "$@"
}

install_project() {
  if command -v uv >/dev/null 2>&1; then
    run_cmd uv pip install -e ".[dev]"
  else
    run_cmd python -m pip install --upgrade pip
    run_cmd python -m pip install -e ".[dev]"
  fi
}

print_header "SKILLCHECK quick trial"
printf '%s\n' "This script runs a safe + risky sample audit and writes outputs to ./.skillcheck"
mkdir -p "$ARTIFACT_DIR"
find "$ARTIFACT_DIR" -type f -delete

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  run_cmd python3 -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

install_project

run_cmd skillcheck lint examples/brand-voice-editor --output-dir "$ARTIFACT_DIR" --policy-pack balanced --policy-version 2
run_cmd skillcheck probe examples/brand-voice-editor --output-dir "$ARTIFACT_DIR" --policy-pack balanced --policy-version 2

print_header "Expected failure checks (risky sample)"
set +e
skillcheck lint examples/risky-net-egress --output-dir "$ARTIFACT_DIR" --policy-pack balanced --policy-version 2
lint_exit=$?
skillcheck probe examples/risky-net-egress --output-dir "$ARTIFACT_DIR" --policy-pack balanced --policy-version 2
probe_exit=$?
set -e

if [ "$lint_exit" -eq 0 ] || [ "$probe_exit" -eq 0 ]; then
  echo "Unexpected pass: risky sample should fail lint and probe checks." >&2
  exit 1
fi

run_cmd skillcheck report . --artifacts "$ARTIFACT_DIR" --summary

print_header "Trial complete"
printf '%s\n' "Human report:  $ROOT_DIR/$ARTIFACT_DIR/results.md"
printf '%s\n' "JSON report:   $ROOT_DIR/$ARTIFACT_DIR/results.json"
printf '%s\n' "Sample docs:   $ROOT_DIR/docs/sample-results.md"
