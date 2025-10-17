"""Internal sandbox runner used by ProbeRunner when exec mode is enabled."""

from __future__ import annotations

import argparse
import builtins
import fnmatch
import json
import os
import runpy
import socket
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Iterable, List
from urllib.parse import urlparse

VIOLATIONS: List[dict] = []


class SandboxViolation(RuntimeError):
    """Raised when sandbox policy is violated."""

    def __init__(self, category: str, detail: str):
        super().__init__(detail)
        self.category = category
        self.detail = detail


def _record(category: str, detail: str) -> None:
    VIOLATIONS.append({"category": category, "detail": detail})


def _normalize_globs(globs: Iterable[str]) -> List[str]:
    values: List[str] = []
    for item in globs:
        if item:
            values.append(item)
    return values


def _relative_to_root(root: Path, candidate: Path) -> str:
    try:
        relative = candidate.resolve().relative_to(root.resolve())
    except Exception:
        return ".."
    return str(relative)


def _apply_fs_guard(skill_root: Path, allow_globs: List[str]) -> None:
    original_open = builtins.open

    def _validate_write_target(target) -> None:
        filepath = Path(target)
        absolute = filepath.resolve() if filepath.is_absolute() else (Path.cwd() / filepath).resolve()
        rel = _relative_to_root(skill_root, absolute)
        if rel == "..":
            detail = f"write to {filepath} escapes skill root"
            _record("write", detail)
            raise SandboxViolation("write", detail)
        if not allow_globs:
            detail = f"write to {rel} not allowed by policy"
            _record("write", detail)
            raise SandboxViolation("write", detail)
        if not any(fnmatch.fnmatch(rel, glob) for glob in allow_globs):
            detail = f"write to {rel} not allowed by policy"
            _record("write", detail)
            raise SandboxViolation("write", detail)

    def sandbox_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "+", "x")):
            _validate_write_target(file)
        return original_open(file, mode, *args, **kwargs)

    builtins.open = sandbox_open  # type: ignore[assignment]

    original_write_text = Path.write_text
    original_write_bytes = Path.write_bytes

    def sandbox_write_text(self: Path, data: str, encoding: str | None = None, errors: str | None = None) -> int:
        _validate_write_target(self)
        return original_write_text(self, data, encoding=encoding, errors=errors)

    def sandbox_write_bytes(self: Path, data: bytes) -> int:
        _validate_write_target(self)
        return original_write_bytes(self, data)

    Path.write_text = sandbox_write_text  # type: ignore[assignment]
    Path.write_bytes = sandbox_write_bytes  # type: ignore[assignment]


def _apply_network_guard(allow_hosts: List[str]) -> None:
    allowed_hosts = set()
    allowed_netlocs = set()
    for host in allow_hosts:
        if not host:
            continue
        allowed_hosts.add(host)
        parsed = urlparse(host)
        if parsed.netloc:
            allowed_netlocs.add(parsed.netloc.lower())

    def _host_allowed(host: str) -> bool:
        if not allowed_hosts:
            return False
        host_lower = host.lower()
        if host_lower in allowed_hosts:
            return True
        return host_lower in allowed_netlocs

    original_create_connection = socket.create_connection
    original_socket = socket.socket

    def sandbox_create_connection(*args, **kwargs):
        address = args[0]
        if isinstance(address, tuple):
            host = address[0]
            if not _host_allowed(host):
                detail = f"socket connect to {host} blocked"
                _record("network", detail)
                raise SandboxViolation("network", detail)
        return original_create_connection(*args, **kwargs)

    class GuardedSocket(socket.socket):  # type: ignore[misc]
        def connect(self, address):
            host = address[0] if isinstance(address, tuple) else str(address)
            if not _host_allowed(host):
                detail = f"socket connect to {host} blocked"
                _record("network", detail)
                raise SandboxViolation("network", detail)
            return super().connect(address)

    sandbox_create_connection.__name__ = "create_connection"  # type: ignore[attr-defined]
    socket.create_connection = sandbox_create_connection  # type: ignore[assignment]
    socket.socket = GuardedSocket  # type: ignore[assignment]

    try:
        import urllib.request  # type: ignore

        original_urlopen = urllib.request.urlopen

        def sandbox_urlopen(url, *args, **kwargs):
            parsed = urlparse(url)
            host = f"{parsed.scheme}://{parsed.netloc}"
            if not _host_allowed(host) and not _host_allowed(parsed.netloc):
                detail = f"urlopen to {host or url} blocked"
                _record("network", detail)
                raise SandboxViolation("network", detail)
            return original_urlopen(url, *args, **kwargs)

        urllib.request.urlopen = sandbox_urlopen  # type: ignore[assignment]
    except Exception:  # pragma: no cover - optional dependency
        pass

    try:
        import requests  # type: ignore

        original_request = requests.sessions.Session.request

        def sandbox_request(self, method, url, *args, **kwargs):
            parsed = urlparse(url)
            host = f"{parsed.scheme}://{parsed.netloc}"
            if not _host_allowed(host) and not _host_allowed(parsed.netloc):
                detail = f"requests.{method.lower()} to {host or url} blocked"
                _record("network", detail)
                raise SandboxViolation("network", detail)
            return original_request(self, method, url, *args, **kwargs)

        requests.sessions.Session.request = sandbox_request  # type: ignore[assignment]
    except Exception:  # pragma: no cover - optional dependency
        pass


def _apply_subprocess_guard() -> None:
    try:
        import subprocess  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        return

    original_popen = subprocess.Popen

    class SandboxPopen(subprocess.Popen):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):
            detail = f"subprocess execution blocked: {args[0] if args else 'unknown'}"
            _record("subprocess", detail)
            raise SandboxViolation("subprocess", detail)

    subprocess.Popen = SandboxPopen  # type: ignore[assignment]


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute a Skill script inside sandbox.")
    parser.add_argument("--script", required=True, help="Relative path to the script inside the skill.")
    parser.add_argument("--skill-root", required=True, help="Root directory of the skill copy.")
    parser.add_argument("--write-allow", action="append", default=[], help="Filesystem write allow globs.")
    parser.add_argument("--network-allow", action="append", default=[], help="Allowed network hosts.")
    args = parser.parse_args()

    skill_root = Path(args.skill_root).resolve()
    script_path = (skill_root / args.script).resolve()
    if not script_path.exists():
        print(json.dumps({"error": f"Script {args.script} not found"}))
        return

    os.environ["SKILLCHECK_SANDBOX"] = "1"
    os.chdir(skill_root)
    _apply_fs_guard(skill_root, _normalize_globs(args.write_allow))
    _apply_network_guard(_normalize_globs(args.network_allow))
    _apply_subprocess_guard()

    stdout_buffer = StringIO()
    stderr_buffer = StringIO()
    result_code = 0

    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        try:
            sys.argv = [str(script_path)]
            runpy.run_path(str(script_path), run_name="__main__")
        except SandboxViolation:
            result_code = 1
        except SystemExit as exc:
            result_code = int(exc.code) if isinstance(exc.code, int) else 1
        except Exception as exc:  # pragma: no cover - defensive
            _record("runtime", f"{type(exc).__name__}: {exc}")
            result_code = 1

    payload = {
        "violations": VIOLATIONS,
        "returncode": result_code,
        "stdout": stdout_buffer.getvalue(),
        "stderr": stderr_buffer.getvalue(),
    }
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
