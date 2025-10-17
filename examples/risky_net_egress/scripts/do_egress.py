#!/usr/bin/env python3
"""
Intentionally risky helper for SKILLCHECK demo:
- Attempts outbound network request.
- Attempts to write outside the allowed scratch/ directory.

This should be blocked by the sandbox/probe stage and flagged in the report.
"""
from urllib.request import urlopen
from pathlib import Path


def main() -> None:
    # Network egress attempt (should be blocked by policy/sandbox)
    try:
        with urlopen("https://example.com", timeout=2) as resp:  # nosec B310 - intentional for demo
            _ = resp.read(128)
    except Exception as exc:  # pragma: no cover - demo output
        print(f"[egress-blocked] {exc!r}")

    # Disallowed write attempt (outside scratch/)
    try:
        Path("../outside.txt").write_text("should be blocked\n", encoding="utf-8")
        print("[write] wrote ../outside.txt (this should be blocked by policy)")
    except Exception as exc:  # pragma: no cover - demo output
        print(f"[write-blocked] {exc!r}")


if __name__ == "__main__":
    main()
