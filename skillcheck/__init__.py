"""Skillcheck package exports."""

from __future__ import annotations

from .cli import app, main
from .schema import (
    Policy,
    SkillMetadata,
    SkillValidationError,
    load_policy,
    load_skill_metadata,
)
from .lint_rules import LintIssue, LintReport, run_lint
from .probe import ProbeResult, ProbeRunner
from .sbom import generate_sbom
from .attest import AttestationBuilder
from .report import ReportWriter
from .bundle import open_skill_bundle, SkillBundleError
from .utils import slugify

__all__ = [
    "app",
    "main",
    "Policy",
    "SkillMetadata",
    "SkillValidationError",
    "load_policy",
    "load_skill_metadata",
    "LintIssue",
    "LintReport",
    "run_lint",
    "ProbeResult",
    "ProbeRunner",
    "generate_sbom",
    "AttestationBuilder",
    "ReportWriter",
    "open_skill_bundle",
    "SkillBundleError",
    "slugify",
]

__version__ = "0.1.0"
