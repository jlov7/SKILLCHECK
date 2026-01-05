# Interpreting Findings & Remediation Guide

Use this table to map SKILLCHECK findings to recommended actions.

| Finding code | Severity | Meaning | Suggested remediation |
| --- | --- | --- | --- |
| `SCHEMA_MISSING` | Error | Missing `SKILL.md` (or malformed frontmatter). | Add a valid `SKILL.md` with YAML frontmatter. |
| `SCHEMA_INVALID` | Error | Frontmatter YAML is invalid or not a mapping. | Fix frontmatter formatting. |
| `FRONTMATTER_*` | Error/Warning | Frontmatter violates Agent Skills schema (name/description/compatibility/allowed-tools). | Update fields to match the spec; keep names lowercase and kebab-case. |
| `SECRET_SUSPECT` | Error | Potential secret (e.g., `API_KEY=`). | Remove the secret or integrate with secure storage. |
| `forbidden_pattern_*` | Error | Matches a policy forbidden regex (e.g., raw `curl`). | Replace with approved integration (e.g., MCP connector) or obtain a waiver. |
| `PATH_TRAVERSAL` | Error | Script references `../` paths. | Confine file access to the Skill directory or allowlists. |
| `REFERENCE_*` | Warning/Error | Missing or unsafe file references in `SKILL.md`. | Fix paths, avoid deep nesting, or move references into `references/`. |
| `DEPENDENCY_*` | Error | Dependency not in allowlist or invalid manifest. | Add an allowlist entry or remove the dependency. |
| `EGRESS_*` | Error | Static probe found a network call (HTTP, requests, httpx). | Remove or justify via policy allowlist/waiver. |
| `WRITE_*` | Error | Static probe found writes outside allowlisted paths. | Redirect writes to approved directories (e.g., `scratch/`). |
| `EGRESS_SANDBOX` | Error | Sandbox execution blocked a network request at runtime. | Review the script; if legitimate, add to policy; otherwise remove. |
| `WRITE_SANDBOX` | Error | Sandbox execution stopped a write outside policy. | Update script or policy as appropriate. |
| `SKILL_MONOLITH` | Warning | `SKILL.md` body exceeds the recommended size (progressive disclosure). | Split content into referenced files for clarity. |
| `notes` entries | Info | Context such as reads outside policy or stdout/stderr logs. | Review for nuance; may inform future policy tweaks. |

General guidance:
- **Error findings** → treat as release blockers unless there’s a documented waiver.
- **Warnings** → review and weigh against business need (e.g., `SKILL_MONOLITH`).
- **Sandbox findings** → pay special attention; they demonstrate runtime behavior.

Keep this handy when triaging SKILLCHECK runs.
