from pathlib import Path

import pytest

from skillcheck.schema import SkillValidationError, load_policy, load_skill_metadata


def _write_skill(tmp_path: Path, name: str, description: str) -> Path:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: "{name}"
description: "{description}"
---

# Body
""",
        encoding="utf-8",
    )
    return skill_dir


def test_load_skill_metadata_valid(tmp_path: Path) -> None:
    description = "A short description well within limits."
    skill_dir = _write_skill(tmp_path, "Valid Skill", description)
    policy = load_policy()
    metadata, body = load_skill_metadata(skill_dir, policy)
    assert metadata.name == "Valid Skill"
    assert metadata.description == description
    assert body.strip().startswith("# Body")


def test_load_skill_metadata_description_too_long(tmp_path: Path) -> None:
    description = "x" * 205
    skill_dir = _write_skill(tmp_path, "Overflow Skill", description)
    policy = load_policy()
    with pytest.raises(SkillValidationError):
        load_skill_metadata(skill_dir, policy)
