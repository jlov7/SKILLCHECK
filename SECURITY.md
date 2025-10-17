# Security Policy

SKILLCHECK is released as a **personal research preview**. It never sends Skill contents outside your machine and runs entirely offline by default.

## Sandbox coverage
- The dynamic probe sandbox blocks network sockets, subprocesses, and disallowed file writes on **macOS** and **Linux**.
- On **Windows**, the probe currently runs in static mode unless you supply your own sandbox; SKILLCHECK still performs linting and heuristic detection.

## Reporting issues
- Please open a private GitHub Security Advisory for vulnerability disclosures (preferred), or file an issue when secrecy is not required. This project is maintained in spare time, so responses may be delayed.
- For policy/waiver questions, open an issue describing the Skill bundle and the policy snippet causing concern.

## Attestations
- When available, Sigstore signing is attempted. Otherwise attestation manifests are emitted with a clear `"mode": "unsigned"` note.

Thank you for helping keep the SKILLCHECK ecosystem safe.
