# Why SKILLCHECK Exists

## The problem

Agent Skills are easy to create and easy to distribute. That speed is useful, but it also creates risk: hidden network egress, unsafe write behavior, weak metadata hygiene, and inconsistent policy enforcement across teams.

When these checks are manual, teams either move too slowly or accept blind spots.

## The goal

SKILLCHECK was built to make pre-enable review of Skills fast, repeatable, and auditable.

It gives engineering, security, and governance teams a shared decision surface:
- What was checked.
- What failed.
- Why it failed.
- What to do next.

## What it does

- **Lint**: static policy checks for schema, secrets, forbidden patterns, and dependencies.
- **Probe**: runtime-oriented heuristics (and optional execution sandboxing) for egress/write behavior.
- **Attest**: provenance artifacts (SBOM + attestation) for audit trails.
- **Report**: one markdown/json summary for both humans and automation.

## Why this matters

Without this layer, teams ship Skills with unknown behavior.

With SKILLCHECK, they can enforce a default-deny posture while keeping delivery fast.

## Scope and philosophy

This project is an independent research effort focused on practical safety and operational clarity:
- Local-first by default.
- Policy-driven governance.
- Clear failure states.
- Evidence over opinion.
