"""Utility helpers for SKILLCHECK."""

from __future__ import annotations

import re

_SLUG_PATTERN = re.compile(r"[^a-zA-Z0-9_.-]+")


def slugify(value: str) -> str:
    """Return a filesystem-friendly slug for artifact names."""
    slug = _SLUG_PATTERN.sub("-", value.lower()).strip("-")
    return slug or "skill"

