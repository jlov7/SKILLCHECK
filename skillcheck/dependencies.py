"""Dependency discovery for skill bundles."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None  # type: ignore


@dataclass
class Dependency:
    ecosystem: str
    name: str
    spec: str
    source: str


@dataclass
class DependencyIssue:
    code: str
    message: str
    path: str


REQ_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*")


def _iter_requirement_files(skill_path: Path) -> Iterable[Path]:
    patterns = ("requirements*.txt", "requirements*.in")
    for pattern in patterns:
        for path in sorted(skill_path.rglob(pattern)):
            if "node_modules" in path.parts:
                continue
            yield path


def _parse_requirement_line(
    line: str, path: Path, issues: List[DependencyIssue]
) -> Optional[Dependency]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith(("-", "--")):
        return None
    if stripped.startswith((".", "/")):
        issues.append(
            DependencyIssue(
                code="DEPENDENCY_PYPI_PATH",
                message=f"Local path dependency is not allowed: {stripped}",
                path=str(path),
            )
        )
        return None
    if "://" in stripped or stripped.startswith("git+"):
        issues.append(
            DependencyIssue(
                code="DEPENDENCY_PYPI_VCS",
                message=f"VCS or URL dependency is not allowed: {stripped}",
                path=str(path),
            )
        )
        return None
    match = REQ_NAME_RE.match(stripped)
    if not match:
        issues.append(
            DependencyIssue(
                code="DEPENDENCY_PYPI_PARSE",
                message=f"Could not parse dependency line: {stripped}",
                path=str(path),
            )
        )
        return None
    name = match.group(0)
    return Dependency(ecosystem="pypi", name=name, spec=stripped, source=str(path))


def _collect_requirements(path: Path, issues: List[DependencyIssue], seen: Set[Path]) -> List[Dependency]:
    if path in seen:
        return []
    seen.add(path)
    deps: List[Dependency] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        issues.append(
            DependencyIssue(
                code="DEPENDENCY_PYPI_MISSING",
                message=f"Referenced requirements file not found: {path}",
                path=str(path),
            )
        )
        return deps
    except UnicodeDecodeError:
        issues.append(
            DependencyIssue(
                code="DEPENDENCY_PYPI_ENCODING",
                message=f"Requirements file is not valid UTF-8: {path}",
                path=str(path),
            )
        )
        return deps

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("-r") or stripped.startswith("--requirement"):
            parts = stripped.split(maxsplit=1)
            if len(parts) == 2:
                ref_path = (path.parent / parts[1]).resolve()
                deps.extend(_collect_requirements(ref_path, issues, seen))
            else:
                issues.append(
                    DependencyIssue(
                        code="DEPENDENCY_PYPI_PARSE",
                        message=f"Could not parse requirement include: {stripped}",
                        path=str(path),
                    )
                )
            continue
        dep = _parse_requirement_line(line, path, issues)
        if dep:
            deps.append(dep)
    return deps


def _parse_pyproject(path: Path, issues: List[DependencyIssue]) -> List[Dependency]:
    deps: List[Dependency] = []
    if tomllib is None:
        issues.append(
            DependencyIssue(
                code="DEPENDENCY_PYPI_TOML",
                message="tomllib/tomli not available; cannot parse pyproject.toml",
                path=str(path),
            )
        )
        return deps
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(
            DependencyIssue(
                code="DEPENDENCY_PYPI_TOML",
                message=f"Failed to parse pyproject.toml: {exc}",
                path=str(path),
            )
        )
        return deps
    project = data.get("project", {})
    requirements = project.get("dependencies", [])
    if isinstance(requirements, list):
        for spec in requirements:
            if isinstance(spec, str):
                match = REQ_NAME_RE.match(spec.strip())
                if match:
                    deps.append(
                        Dependency(ecosystem="pypi", name=match.group(0), spec=spec, source=str(path))
                    )
            else:
                issues.append(
                    DependencyIssue(
                        code="DEPENDENCY_PYPI_PARSE",
                        message=f"Invalid dependency entry in pyproject.toml: {spec!r}",
                        path=str(path),
                    )
                )
    elif requirements:
        issues.append(
            DependencyIssue(
                code="DEPENDENCY_PYPI_PARSE",
                message="project.dependencies must be a list",
                path=str(path),
            )
        )
    optional = project.get("optional-dependencies", {})
    if isinstance(optional, dict):
        for group in optional.values():
            if not isinstance(group, list):
                continue
            for spec in group:
                if isinstance(spec, str):
                    match = REQ_NAME_RE.match(spec.strip())
                    if match:
                        deps.append(
                            Dependency(ecosystem="pypi", name=match.group(0), spec=spec, source=str(path))
                        )
    return deps


def _parse_package_json(path: Path, issues: List[DependencyIssue]) -> List[Dependency]:
    deps: List[Dependency] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(
            DependencyIssue(
                code="DEPENDENCY_NPM_PARSE",
                message=f"Failed to parse package.json: {exc}",
                path=str(path),
            )
        )
        return deps
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        section_data = data.get(section)
        if section_data is None:
            continue
        if not isinstance(section_data, dict):
            issues.append(
                DependencyIssue(
                    code="DEPENDENCY_NPM_PARSE",
                    message=f"{section} must be an object",
                    path=str(path),
                )
            )
            continue
        for name, version in section_data.items():
            if not isinstance(version, str):
                issues.append(
                    DependencyIssue(
                        code="DEPENDENCY_NPM_PARSE",
                        message=f"Invalid version for {name}: {version!r}",
                        path=str(path),
                    )
                )
                continue
            deps.append(
                Dependency(
                    ecosystem="npm",
                    name=str(name),
                    spec=f"{name}@{version}",
                    source=str(path),
                )
            )
    return deps


def collect_dependencies(skill_path: Path) -> Tuple[List[Dependency], List[DependencyIssue]]:
    """Collect dependencies and parse issues from common manifest files."""
    dependencies: List[Dependency] = []
    issues: List[DependencyIssue] = []

    seen_requirements: Set[Path] = set()
    for path in _iter_requirement_files(skill_path):
        dependencies.extend(_collect_requirements(path, issues, seen_requirements))

    pyproject = skill_path / "pyproject.toml"
    if pyproject.exists():
        dependencies.extend(_parse_pyproject(pyproject, issues))

    for path in sorted(skill_path.rglob("package.json")):
        if "node_modules" in path.parts:
            continue
        dependencies.extend(_parse_package_json(path, issues))

    return dependencies, issues
