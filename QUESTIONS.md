# Questions

Resolved decisions (set on February 15, 2026):

1. Distribution target (v1):
   - Use GitHub Releases as the canonical distribution channel (source + wheel artifacts).
   - Keep repo-install (`pip install -e .`) fully supported.
   - Defer PyPI publishing until after a stabilization cycle (post-v1).

2. Platform support (v1):
   - Official support: macOS and Linux.
   - Windows is best-effort for static flows (`lint`, `report`, `attest`) and not an execution-sandbox target for v1.

3. Attestation signing default (v1):
   - Unsigned attestation is acceptable by default.
   - Signed attestation remains opt-in when `attest` extras + signing infrastructure are available.

4. CI provider and required checks (v1):
   - GitHub Actions is the required CI provider for this repo.
   - Require the SKILLCHECK workflow status checks before merge.

5. Trust gate default (v1.1+):
   - Default to `--release-gate standard` in CI.
   - Use `strict` for release branches/tags or higher-assurance environments.
