"""Utilities for loading Skill bundles from directories or archives."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class SkillBundleError(ValueError):
    """Raised when a Skill bundle cannot be loaded."""


def _has_skill_md(root: Path) -> bool:
    return (root / "SKILL.md").exists() or (root / "skill.md").exists()


def _find_skill_root(extracted_root: Path) -> Path:
    if _has_skill_md(extracted_root):
        return extracted_root
    candidates = [
        child for child in extracted_root.iterdir() if child.name != "__MACOSX"
    ]
    if len(candidates) == 1 and candidates[0].is_dir() and _has_skill_md(candidates[0]):
        return candidates[0]
    for candidate in candidates:
        if candidate.is_dir() and _has_skill_md(candidate):
            return candidate
    raise SkillBundleError("Archive does not contain a SKILL.md (or skill.md) file")


def _safe_extract(archive: zipfile.ZipFile, target_root: Path) -> None:
    target_root = target_root.resolve()
    for info in archive.infolist():
        member = Path(info.filename)
        if member.is_absolute() or ".." in member.parts:
            raise SkillBundleError(f"Archive contains unsafe path: {info.filename}")
        destination = (target_root / member).resolve()
        if target_root not in destination.parents and destination != target_root:
            raise SkillBundleError(f"Archive path escapes target: {info.filename}")
        if info.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as src, destination.open("wb") as dst:
            shutil.copyfileobj(src, dst)


@contextmanager
def open_skill_bundle(path: Path) -> Iterator[Path]:
    """Yield a directory containing a Skill, expanding archives as needed."""
    path = Path(path)
    if path.is_dir():
        if not _has_skill_md(path):
            raise SkillBundleError(f"Directory {path} is missing SKILL.md (or skill.md)")
        yield path
        return
    if path.is_file() and path.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            with zipfile.ZipFile(path) as archive:
                _safe_extract(archive, temp_root)
            skill_root = _find_skill_root(temp_root)
            yield skill_root
        return
    raise SkillBundleError(f"Unsupported skill bundle: {path}")
