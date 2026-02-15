# Release-ready v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a release-ready v1 with clear CLI onboarding/help, robust failure UX, quality gates, and complete documentation.

**Architecture:** Keep SKILLCHECK as a CLI-first tool. Add onboarding/help as lightweight CLI output, improve empty-state messaging in the report path, and extend docs/CI to reflect v1 quality gates.

**Tech Stack:** Python 3.10+, Typer, Rich, Ruff, Mypy, Pytest.

---

### Task 1: Add first-run onboarding output

**Files:**
- Modify: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/skillcheck/cli.py`
- Test: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/tests/test_cli.py`

**Step 1: Write the failing test**
```python
from typer.testing import CliRunner
from skillcheck.cli import app

def test_cli_first_run_shows_quickstart():
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Quickstart" in result.output
    assert "skillcheck lint" in result.output
```

**Step 2: Run test to verify it fails**
Run: `pytest -q tests/test_cli.py::test_cli_first_run_shows_quickstart`
Expected: FAIL with missing output.

**Step 3: Write minimal implementation**
```python
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print("SKILLCHECK — Audit Agent Skills", style="bold")
        console.print("Quickstart:\n  skillcheck lint <path>\n  skillcheck probe <path>\n  skillcheck report .")
        raise typer.Exit(code=0)
```

**Step 4: Run test to verify it passes**
Run: `pytest -q tests/test_cli.py::test_cli_first_run_shows_quickstart`
Expected: PASS

**Step 5: Commit**
```bash
git add /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/skillcheck/cli.py \
  /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/tests/test_cli.py

git commit -m "feat: add first-run quickstart" -m "Improve onboarding when running without args" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 2: Add in-app help command

**Files:**
- Modify: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/skillcheck/cli.py`
- Test: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/tests/test_cli.py`

**Step 1: Write the failing test**
```python
def test_cli_help_command_outputs_guidance():
    runner = CliRunner()
    result = runner.invoke(app, ["help"])
    assert result.exit_code == 0
    assert "Help" in result.output
    assert "docs/help.md" in result.output
```

**Step 2: Run test to verify it fails**
Run: `pytest -q tests/test_cli.py::test_cli_help_command_outputs_guidance`
Expected: FAIL (command not found).

**Step 3: Write minimal implementation**
```python
@app.command()
def help() -> None:
    console.print("Help — SKILLCHECK", style="bold")
    console.print("Docs: docs/help.md")
```

**Step 4: Run test to verify it passes**
Run: `pytest -q tests/test_cli.py::test_cli_help_command_outputs_guidance`
Expected: PASS

**Step 5: Commit**
```bash
git add /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/skillcheck/cli.py \
  /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/tests/test_cli.py

git commit -m "feat: add in-app help command" -m "Provide a compact help entrypoint" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 3: Improve report empty-state messaging

**Files:**
- Modify: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/skillcheck/cli.py`
- Test: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/tests/test_cli.py`

**Step 1: Write the failing test**
```python
from pathlib import Path

def test_report_empty_state_message(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(app, ["report", str(tmp_path), "--summary"])
    assert result.exit_code == 0
    assert "No skill artifacts found" in result.output
```

**Step 2: Run test to verify it fails**
Run: `pytest -q tests/test_cli.py::test_report_empty_state_message`
Expected: FAIL (message missing).

**Step 3: Write minimal implementation**
```python
if not result.rows:
    console.print("No skill artifacts found. Run lint/probe first.", style="yellow")
```

**Step 4: Run test to verify it passes**
Run: `pytest -q tests/test_cli.py::test_report_empty_state_message`
Expected: PASS

**Step 5: Commit**
```bash
git add /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/skillcheck/cli.py \
  /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/tests/test_cli.py

git commit -m "feat: clarify report empty state" -m "Guide users when no artifacts are present" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 4: Add minimal help doc page

**Files:**
- Create: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/docs/help.md`
- Modify: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/README.md`

**Step 1: Write the failing test**
```python
from pathlib import Path

def test_help_doc_exists():
    assert Path("docs/help.md").exists()
```

**Step 2: Run test to verify it fails**
Run: `pytest -q tests/test_cli.py::test_help_doc_exists`
Expected: FAIL (file missing).

**Step 3: Write minimal implementation**
Create `docs/help.md` with a compact quickstart, common errors, and pointers to walkthroughs.

**Step 4: Run test to verify it passes**
Run: `pytest -q tests/test_cli.py::test_help_doc_exists`
Expected: PASS

**Step 5: Commit**
```bash
git add /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/docs/help.md \
  /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/README.md

git commit -m "docs: add minimal help page" -m "Provide a docs entrypoint for onboarding" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 5: Add build gate to dev tooling + CI

**Files:**
- Modify: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/pyproject.toml`
- Modify: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/.github/workflows/skillcheck.yml`
- Test: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/tests/test_cli.py`

**Step 1: Write the failing test**
```python
import tomllib
from pathlib import Path

def test_build_dependency_declared():
    data = tomllib.loads(Path("pyproject.toml").read_text())
    dev_deps = data["project"]["optional-dependencies"]["dev"]
    assert any(dep.startswith("build") for dep in dev_deps)
```

**Step 2: Run test to verify it fails**
Run: `pytest -q tests/test_cli.py::test_build_dependency_declared`
Expected: FAIL (build not listed).

**Step 3: Write minimal implementation**
Add `build>=1.2.0` to the `dev` extras and add a `python -m build` step in CI.

**Step 4: Run test to verify it passes**
Run: `pytest -q tests/test_cli.py::test_build_dependency_declared`
Expected: PASS

**Step 5: Commit**
```bash
git add /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/pyproject.toml \
  /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/.github/workflows/skillcheck.yml \
  /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/tests/test_cli.py

git commit -m "chore: add build gate" -m "Ensure packaging build runs in CI" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 6: Update README with local setup/run/test/deploy/env var notes

**Files:**
- Modify: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/README.md`

**Step 1: Write the failing test**
```python
from pathlib import Path

def test_readme_mentions_deploy_and_env_vars():
    content = Path("README.md").read_text()
    assert "Deploy" in content or "Release" in content
    assert "Environment variables" in content or "Env vars" in content
```

**Step 2: Run test to verify it fails**
Run: `pytest -q tests/test_cli.py::test_readme_mentions_deploy_and_env_vars`
Expected: FAIL

**Step 3: Write minimal implementation**
Add README sections for local setup, run, tests, deploy/release, and environment variables.

**Step 4: Run test to verify it passes**
Run: `pytest -q tests/test_cli.py::test_readme_mentions_deploy_and_env_vars`
Expected: PASS

**Step 5: Commit**
```bash
git add /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/README.md \
  /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/tests/test_cli.py

git commit -m "docs: expand README for v1" -m "Add setup/run/test/deploy/env var notes" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 7: Final verification and release report

**Files:**
- Modify: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/PLANS.md`
- Modify: `/Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/RELEASE_CHECKLIST.md`

**Step 1: Run verification gates**
Run:
- `ruff check .`
- `mypy skillcheck`
- `pytest -q`
- `python -m build`
Expected: All pass.

**Step 2: Update plan + checklist**
Mark milestones and checklist items complete.

**Step 3: Commit**
```bash
git add /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/PLANS.md \
  /Users/jasonlovell/AI/Work Prototypes/SKILLCHECK/.worktrees/release-ready-v1/RELEASE_CHECKLIST.md

git commit -m "chore: finalize v1 release readiness" -m "Record completion status and verification" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```
