from pathlib import Path

import pytest

from skillcheck.schema import SkillValidationError, load_policy, load_skill_metadata


def _write_skill(tmp_path: Path, name: str, description: str) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: {name}
description: "{description}"
---

# Body
""",
        encoding="utf-8",
    )
    return skill_dir


def test_load_skill_metadata_valid(tmp_path: Path) -> None:
    description = "A short description well within limits."
    skill_dir = _write_skill(tmp_path, "valid-skill", description)
    policy = load_policy()
    metadata, body = load_skill_metadata(skill_dir, policy)
    assert metadata.name == "valid-skill"
    assert metadata.description == description
    assert body.strip().startswith("# Body")


def test_load_skill_metadata_description_too_long(tmp_path: Path) -> None:
    description = "x" * 1100
    skill_dir = _write_skill(tmp_path, "overflow-skill", description)
    policy = load_policy()
    with pytest.raises(SkillValidationError):
        load_skill_metadata(skill_dir, policy)


def test_load_skill_metadata_name_mismatch(tmp_path: Path) -> None:
    skill_dir = tmp_path / "dir-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: other-skill
description: "Mismatch demo."
---

# Body
""",
        encoding="utf-8",
    )
    policy = load_policy()
    with pytest.raises(SkillValidationError):
        load_skill_metadata(skill_dir, policy)


def test_load_policy_pack_by_name() -> None:
    policy = load_policy(policy_pack="strict")
    assert policy.raw.get("pack") == "strict"
    assert policy.raw.get("version") == 2


def test_load_all_policy_packs() -> None:
    for pack in ("strict", "balanced", "research", "enterprise"):
        policy = load_policy(policy_pack=pack)
        assert policy.raw.get("pack") == pack


def test_load_policy_pack_version_mismatch() -> None:
    with pytest.raises(SkillValidationError):
        load_policy(policy_pack="balanced", expected_version=999)
