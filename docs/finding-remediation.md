# Interpreting Findings & Remediation Guide

Use this table to map SKILLCHECK findings to recommended actions.

| Finding code | Severity | Meaning | Suggested remediation |
| --- | --- | --- | --- |
| `SCHEMA_INVALID` | Error | `SKILL.md` metadata is missing/invalid/too long. | Fix front matter (name/description length, required fields). |
| `SECRET_SUSPECT` | Error | Potential secret (e.g., `API_KEY=`). | Remove the secret or integrate with secure storage.
| `forbidden_pattern_*` | Error | Matches a policy forbidden regex (e.g., raw `curl`). | Replace with approved integration (e.g., MCP connector) or obtain a waiver. |
| `PATH_TRAVERSAL` | Error | Script references `../` paths. | Confine file access to the Skill directory or allowlists. |
| `EGRESS_*` | Error | Static probe found a network call (HTTP, requests, httpx). | Remove or justify via policy allowlist/waiver. |
| `WRITE_*` | Error | Static probe found writes outside allowlisted paths. | Redirect writes to approved directories (e.g., `scratch/`). |
| `EGRESS_SANDBOX` | Error | Sandbox execution blocked a network request at runtime. | Review the script; if legitimate, add to policy; otherwise remove. |
| `WRITE_SANDBOX` | Error | Sandbox execution stopped a write outside policy. | Update script or policy as appropriate. |
| `SKILL_MONOLITH` | Warning | Markdown body is very large (suggests progressive disclosure). | Split content into referenced files for clarity. |
| `notes` entries | Info | Context such as reads outside policy or stdout/stderr logs. | Review for nuance; may inform future policy tweaks. |

General guidance:
- **Error findings** → treat as release blockers unless there’s a documented waiver.
- **Warnings** → review and weigh against business need (e.g., `SKILL_MONOLITH`).
- **Sandbox findings** → pay special attention; they demonstrate runtime behavior.

Keep this handy when triaging SKILLCHECK runs.

