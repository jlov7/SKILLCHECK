"""Dynamic probe heuristics for SKILLCHECK."""

from __future__ import annotations

import fnmatch
import re
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from .schema import Policy, parse_skill_metadata

PYTHON_EGRESS_PATTERNS = [
    ("requests_call", re.compile(r"requests\.(?:get|post|delete|put)\(\s*['\"](?P<url>https?://[^'\"]+)")),
    ("urllib_urlopen", re.compile(r"urlopen\(\s*['\"](?P<url>https?://[^'\"]+)")),
    ("httpx_client", re.compile(r"httpx\.\w+\(\s*['\"](?P<url>https?://[^'\"]+)")),
]
JS_EGRESS_PATTERNS = [
    ("fetch_call", re.compile(r"\bfetch\(\s*['\"](?P<url>https?://[^'\"]+)")),
    ("axios_call", re.compile(r"\baxios\.(?:get|post|delete|put|patch)\(\s*['\"](?P<url>https?://[^'\"]+)")),
    ("node_http", re.compile(r"\bhttps?\.request\(\s*['\"](?P<url>https?://[^'\"]+)")),
]
SHELL_EGRESS_PATTERNS = [
    ("curl_http", re.compile(r"\bcurl\s+(?P<url>https?://[^\s'\"`]+)")),
    ("wget_http", re.compile(r"\bwget\s+(?P<url>https?://[^\s'\"`]+)")),
]
POWERSHELL_EGRESS_PATTERNS = [
    ("powershell_webrequest", re.compile(r"\bInvoke-(?:WebRequest|RestMethod)\s+-Uri\s+(?P<url>https?://[^\s'\"`]+)", re.IGNORECASE)),
]

PYTHON_WRITE_PATTERNS = [
    ("open_write", re.compile(r"open\(\s*['\"](?P<path>[^'\"]+)['\"]\s*,\s*['\"][^'\"]*[wax+][^'\"]*['\"]")),
    ("path_write_text", re.compile(r"Path\(\s*['\"](?P<path>[^'\"]+)['\"]\)\.write_text")),
    ("path_write_bytes", re.compile(r"Path\(\s*['\"](?P<path>[^'\"]+)['\"]\)\.write_bytes")),
    ("os_remove", re.compile(r"os\.remove\(\s*['\"](?P<path>[^'\"]+)['\"]\)")),
]
JS_WRITE_PATTERNS = [
    ("fs_writefile", re.compile(r"fs(?:\.promises)?\.writeFile(?:Sync)?\(\s*['\"](?P<path>[^'\"]+)")),
    ("fs_appendfile", re.compile(r"fs(?:\.promises)?\.appendFile(?:Sync)?\(\s*['\"](?P<path>[^'\"]+)")),
    ("fs_writestream", re.compile(r"fs\.createWriteStream\(\s*['\"](?P<path>[^'\"]+)")),
]
SHELL_WRITE_PATTERNS = [
    ("shell_redirect", re.compile(r"(?:^|\\s)(?:>>|>)\\s*(?P<path>[^\\s&;|]+)")),
    ("shell_tee", re.compile(r"\\btee\\s+(?P<path>[^\\s]+)")),
]

SANDBOX_MODULE = "skillcheck._sandbox_runner"
DEFAULT_EXEC_GLOBS = ["scripts/**/*.py", "*.py"]
IGNORE_DIRS = {".git", ".skillcheck", "__pycache__", "node_modules"}
JS_EXTENSIONS = {".js", ".ts", ".mjs", ".cjs"}
SHELL_EXTENSIONS = {".sh", ".bash", ".zsh", ".ksh", ".cmd", ".bat"}
POWERSHELL_EXTENSIONS = {".ps1", ".psm1"}


@dataclass
class ProbeFinding:
    code: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass
class ProbeResult:
    skill_name: str
    skill_version: Optional[str]
    files_loaded_count: int
    egress_attempts: List[ProbeFinding] = field(default_factory=list)
    disallowed_writes: List[ProbeFinding] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    policy_hash: str = ""

    @property
    def ok(self) -> bool:
        return not self.egress_attempts and not self.disallowed_writes

    def to_dict(self) -> Dict[str, object]:
        return {
            "skill": {"name": self.skill_name, "version": self.skill_version},
            "summary": {
                "files_loaded_count": self.files_loaded_count,
                "egress_attempts": len(self.egress_attempts),
                "disallowed_writes": len(self.disallowed_writes),
            },
            "egress_attempts": [finding.to_dict() for finding in self.egress_attempts],
            "disallowed_writes": [finding.to_dict() for finding in self.disallowed_writes],
            "notes": self.notes,
            "policy_hash": self.policy_hash,
        }


class ProbeRunner:
    """Main entrypoint for dynamic probe heuristics."""

    def __init__(self, policy: Policy, enable_exec: Optional[bool] = None):
        self.policy = policy
        env_flag = os.environ.get("SKILLCHECK_PROBE_EXEC", "").lower() in {"1", "true", "yes"}
        probe_cfg = policy.raw.get("probe", {})
        if not isinstance(probe_cfg, dict):
            probe_cfg = {}
        policy_flag = bool(probe_cfg.get("enable_exec", False))
        if enable_exec is None:
            self.enable_exec = env_flag or policy_flag
        else:
            self.enable_exec = enable_exec
        self.exec_globs = list(probe_cfg.get("exec_globs") or DEFAULT_EXEC_GLOBS)
        self.exec_timeout = float(probe_cfg.get("timeout", 5))

    def run(self, skill_path: Path) -> ProbeResult:
        parse_result = parse_skill_metadata(skill_path, self.policy)
        metadata = parse_result.metadata
        files_loaded = 0
        egress_findings: List[ProbeFinding] = []
        write_findings: List[ProbeFinding] = []
        notes: List[str] = []
        if parse_result.issues:
            for issue in parse_result.issues:
                notes.append(f"Schema issue {issue.code}: {issue.message}")

        for rel_path, text in self._iter_text_files(skill_path):
            if self.policy.is_read_allowed(rel_path):
                files_loaded += 1
            else:
                notes.append(f"Read outside policy allowlist ignored: {rel_path}")
            egress_findings.extend(self._detect_egress(rel_path, text))
            write_findings.extend(self._detect_writes(rel_path, text))

        if self.enable_exec:
            exec_egress, exec_writes, exec_notes = self._run_exec_checks(skill_path)
            egress_findings.extend(exec_egress)
            write_findings.extend(exec_writes)
            notes.extend(exec_notes)

        return ProbeResult(
            skill_name=metadata.name or skill_path.name,
            skill_version=metadata.version,
            files_loaded_count=files_loaded,
            egress_attempts=egress_findings,
            disallowed_writes=write_findings,
            notes=notes,
            policy_hash=self.policy.sha256,
        )

    def _iter_text_files(self, skill_path: Path) -> Iterable[tuple[str, str]]:
        for file_path in sorted(skill_path.rglob("*")):
            if any(part in IGNORE_DIRS for part in file_path.parts):
                continue
            if not file_path.is_file():
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            rel = str(file_path.relative_to(skill_path))
            yield rel, text

    def _detect_egress(self, rel_path: str, text: str) -> List[ProbeFinding]:
        findings: List[ProbeFinding] = []
        ext = Path(rel_path).suffix.lower()
        in_scripts = rel_path.startswith("scripts/")
        patterns: List[Tuple[str, re.Pattern[str]]] = []
        if ext == ".py" or in_scripts:
            patterns.extend(PYTHON_EGRESS_PATTERNS)
        if ext in JS_EXTENSIONS or in_scripts:
            patterns.extend(JS_EGRESS_PATTERNS)
        if ext in SHELL_EXTENSIONS or in_scripts:
            patterns.extend(SHELL_EGRESS_PATTERNS)
        if ext in POWERSHELL_EXTENSIONS or in_scripts:
            patterns.extend(POWERSHELL_EGRESS_PATTERNS)
        for code, pattern in patterns:
            for match in pattern.finditer(text):
                url = match.groupdict().get("url", "")
                host_allowed = self._host_allowed(url)
                if not host_allowed:
                    findings.append(
                        ProbeFinding(
                            code=f"EGRESS_{code.upper()}",
                            message=f"{rel_path}: outbound call to {url} blocked by policy",
                        )
                    )
        return findings

    def _host_allowed(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        if not parsed.netloc:
            return False
        host = f"{parsed.scheme}://{parsed.netloc}"
        if not self.policy.allow_network_hosts:
            return False
        for pattern in self.policy.allow_network_hosts:
            if not pattern:
                continue
            if "://" in pattern:
                if fnmatch.fnmatch(host, pattern):
                    return True
            else:
                if fnmatch.fnmatch(parsed.netloc, pattern):
                    return True
        return False

    def _detect_writes(self, rel_path: str, text: str) -> List[ProbeFinding]:
        findings: List[ProbeFinding] = []
        ext = Path(rel_path).suffix.lower()
        in_scripts = rel_path.startswith("scripts/")
        patterns: List[Tuple[str, re.Pattern[str]]] = []
        if ext == ".py" or in_scripts:
            patterns.extend(PYTHON_WRITE_PATTERNS)
        if ext in JS_EXTENSIONS or in_scripts:
            patterns.extend(JS_WRITE_PATTERNS)
        if ext in SHELL_EXTENSIONS or in_scripts:
            patterns.extend(SHELL_WRITE_PATTERNS)
        for code, pattern in patterns:
            for match in pattern.finditer(text):
                target = match.groupdict().get("path", "")
                normalized = target.strip()
                if not normalized:
                    continue
                if normalized.startswith("../") or normalized.startswith("..\\"):
                    findings.append(
                        ProbeFinding(
                            code=f"WRITE_{code.upper()}",
                            message=f"{rel_path}: attempt to access {normalized} escapes skill root",
                        )
                    )
                    continue
                if normalized.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:\\\\", normalized):
                    findings.append(
                        ProbeFinding(
                            code=f"WRITE_{code.upper()}",
                            message=f"{rel_path}: absolute path write to {normalized} blocked",
                        )
                    )
                    continue
                if not self.policy.is_write_allowed(normalized):
                    findings.append(
                        ProbeFinding(
                            code=f"WRITE_{code.upper()}",
                            message=f"{rel_path}: write to '{normalized}' not covered by policy allowlist",
                        )
                    )
        return findings

    def _run_exec_checks(self, skill_path: Path) -> Tuple[List[ProbeFinding], List[ProbeFinding], List[str]]:
        egress: List[ProbeFinding] = []
        writes: List[ProbeFinding] = []
        notes: List[str] = []
        targets = self._collect_exec_targets(skill_path)
        if not targets:
            return egress, writes, notes
        for script in targets:
            rel = script.relative_to(skill_path)
            notes.append(f"Sandbox exec: {rel}")
            outcome = self._invoke_sandbox(skill_path, script)
            if outcome.get("timeout"):
                notes.append(f"Sandbox timeout while executing {rel} (>{self.exec_timeout}s)")
                continue
            payload = outcome.get("payload")
            if not isinstance(payload, dict):
                notes.append(f"Sandbox returned invalid payload for {rel}")
                continue
            payload_dict: Dict[str, object] = payload
            violations = payload_dict.get("violations")
            if isinstance(violations, list):
                violation_items = violations
            else:
                violation_items = []
            for violation in violation_items:
                category = violation.get("category")
                detail = violation.get("detail", "")
                if category == "network":
                    egress.append(
                        ProbeFinding(
                            code="EGRESS_SANDBOX",
                            message=f"{rel}: {detail}",
                        )
                    )
                elif category == "write":
                    writes.append(
                        ProbeFinding(
                            code="WRITE_SANDBOX",
                            message=f"{rel}: {detail}",
                        )
                    )
                else:
                    notes.append(f"{rel}: sandbox noted {category} -> {detail}")
            stdout_val = payload_dict.get("stdout")
            if isinstance(stdout_val, str) and stdout_val.strip():
                snippet = stdout_val.strip()
                if snippet:
                    notes.append(f"{rel} stdout: {snippet[:200]}")
            stderr_val = outcome.get("stderr")
            if isinstance(stderr_val, str):
                stderr_snippet = stderr_val.strip()
                if stderr_snippet:
                    notes.append(f"{rel} stderr: {stderr_snippet[:200]}")
        return egress, writes, notes

    def _collect_exec_targets(self, skill_path: Path) -> List[Path]:
        targets: List[Path] = []
        seen: set = set()
        for pattern in self.exec_globs:
            for candidate in skill_path.glob(pattern):
                if not candidate.is_file():
                    continue
                if candidate.suffix.lower() != ".py":
                    continue
                key = candidate.resolve()
                if key in seen:
                    continue
                seen.add(key)
                targets.append(candidate)
        return sorted(targets)

    def _invoke_sandbox(self, skill_path: Path, script_path: Path) -> Dict[str, object]:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir) / "skill"
            shutil.copytree(skill_path, temp_root)
            rel_script = script_path.relative_to(skill_path)
            cmd = [
                sys.executable,
                "-m",
                SANDBOX_MODULE,
                "--script",
                str(rel_script),
                "--skill-root",
                str(temp_root),
            ]
            for glob in self.policy.write_globs:
                cmd.extend(["--write-allow", glob])
            for host in self.policy.allow_network_hosts:
                cmd.extend(["--network-allow", host])
            try:
                result = subprocess.run(
                    cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.exec_timeout,
                    cwd=temp_root,
                )
            except subprocess.TimeoutExpired:
                return {"timeout": True}
            stdout = (result.stdout or "").strip()
            payload = {}
            if stdout:
                try:
                    payload = json.loads(stdout.splitlines()[-1])
                except json.JSONDecodeError:
                    payload = {}
            return {
                "payload": payload,
                "stderr": (result.stderr or "").strip(),
                "returncode": result.returncode,
                "timeout": False,
            }
