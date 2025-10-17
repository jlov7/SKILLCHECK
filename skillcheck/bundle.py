"""Utilities for loading Skill bundles from directories or archives."""

from __future__ import annotations

import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class SkillBundleError(ValueError):
    """Raised when a Skill bundle cannot be loaded."""


def _find_skill_root(extracted_root: Path) -> Path:
    if (extracted_root / "SKILL.md").exists():
        return extracted_root
    candidates = [
        child for child in extracted_root.iterdir() if child.name != "__MACOSX"
    ]
    if len(candidates) == 1 and candidates[0].is_dir() and (candidates[0] / "SKILL.md").exists():
        return candidates[0]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / "SKILL.md").exists():
            return candidate
    raise SkillBundleError("Archive does not contain a SKILL.md file")


@contextmanager
def open_skill_bundle(path: Path) -> Iterator[Path]:
    """Yield a directory containing a Skill, expanding archives as needed."""
    path = Path(path)
    if path.is_dir():
        if not (path / "SKILL.md").exists():
            raise SkillBundleError(f"Directory {path} is missing SKILL.md")
        yield path
        return
    if path.is_file() and path.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            with zipfile.ZipFile(path) as archive:
                archive.extractall(temp_root)
            skill_root = _find_skill_root(temp_root)
            yield skill_root
        return
    raise SkillBundleError(f"Unsupported skill bundle: {path}")
