# Policy Cookbook

SKILLCHECK policies are YAML files with deny-by-default semantics. Use these snippets to tailor policies for common scenarios.

## Base policy (deny egress & writes)

```yaml
version: 2
limits:
  skill_name_max: 64
  skill_description_max: 1024
  skill_compatibility_max: 500
  skill_body_max_lines: 500

frontmatter:
  allow_unknown_fields: false
  legacy_fields: []

allow:
  network:
    hosts: []
  filesystem:
    read_globs:
      - "SKILL.md"
      - "skill.md"
      - "*.md"
      - "*.txt"
      - "*.json"
      - "*.toml"
      - "**/*.md"
      - "**/*.txt"
      - "**/*.json"
      - "**/*.toml"
    write_globs:
      - "scratch/**"
  tools:
    allowlist: []

dependencies:
  allow_pypi: []
  allow_npm: []

forbidden_patterns:
  - pattern: "(?i)api[_-]?key|secret|token\\s*[:=]"
    reason: "Potential secret detected."

probe:
  enable_exec: false
  exec_globs:
    - "scripts/**/*.py"
    - "*.py"
  timeout: 5
```

## Allowing egress to a single host

```yaml
allow:
  network:
    hosts:
      - "https://api.example.com"
```

Remember to document this in your attestation or waiver justification.

## Enabling sandbox execution globally

```yaml
probe:
  enable_exec: true
  exec_globs:
    - "scripts/**/*.py"
    - "**/*.py"
  timeout: 10
```

This ensures Python scripts are executed in the sandbox on every run.

## Allowing additional writable directories

```yaml
allow:
  filesystem:
    write_globs:
      - "scratch/**"
      - "tmp/**"
```

## Permitting dependency installation

```yaml
dependencies:
  allow_pypi:
    - "requests==2.*"
    - "pydantic>=2.0,<3.0"
  allow_npm:
    - "yaml"
```

## Allowing specific tools in `allowed-tools`

```yaml
allow:
  tools:
    allowlist:
      - "Bash(*)"
      - "Read"
      - "Write(scratch/**)"
```

If the allowlist is empty, `allowed-tools` is accepted but not enforced.

## Recording a waiver

```yaml
waivers:
  - path: "examples/my_skill/scripts/task.sh"
    rule: "forbidden_pattern_2"
    justification: "Calls out via approved proxy"
```

Waivers should be rare and always justified; the attestation includes them for audit purposes.

## Tips

- Keep base policies in source control, layer environment-specific overrides via `--policy`.
- After editing a policy, rerun `python -m skillcheck.cli lint --policy new.policy.yaml ...` to confirm there are no schema errors.
- Policies are just YAML—consider templating (e.g., with Jinja) for large organizations.
