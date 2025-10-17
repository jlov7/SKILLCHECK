# Security Policy

SKILLCHECK is released as a **research preview**. It never sends Skill contents outside your machine and runs entirely offline by default.

## Sandbox coverage
- The dynamic probe sandbox blocks network sockets, subprocesses, and disallowed file writes on **macOS** and **Linux**.
- On **Windows**, the probe currently runs in static mode unless you supply your own sandbox; SKILLCHECK still performs linting and heuristic detection.

## Reporting issues
- Please open a GitHub Security Advisory or email the maintainer listed in `pyproject.toml` for vulnerability reports.
- For policy/waiver questions, describe the Skill bundle and the policy snippet causing concern.

## Attestations
- When available, Sigstore signing is attempted. Otherwise attestation manifests are emitted with a clear `"mode": "unsigned"` note.

Thank you for helping keep the SKILLCHECK ecosystem safe.

