#!/usr/bin/env python3
"""Scan repository files for likely hard-coded secrets.

This is the Junie-facing CLI entry point for the repository's secret-scan
workflow. It scans files already on disk and exits ``1`` when any likely secret
is found, else ``0``.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PATTERNS: dict[str, re.Pattern[str]] = {
    "AWS access key id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "AWS secret access key": re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}"),
    "Anthropic API key": re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    "OpenAI API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{20,}"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    "Private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    "Generic assigned secret": re.compile(
        r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*['\"](?P<value>[^'\"\s]{8,})['\"]"
    ),
    "Postgres URL with password": re.compile(r"postg(?:res|resql)://[^:\s]+:[^@\s]+@"),
}

ADDRESS_EXEMPT_TYPES = frozenset({"Generic assigned secret"})
_MEM_ADDRESS_RE = re.compile(r"0[xX][0-9a-fA-F]{1,16}[uUlL]{0,3}")

ALLOWLIST = (
    "example",
    "placeholder",
    "your-",
    "your_",
    "changeme",
    "dummy",
    "xxxx",
    "${",
    "<your",
    "redacted",
    "fake",
    "test",
)

SKIP_SUFFIXES = {".lock", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".dmp", ".db"}


def _is_placeholder(line: str) -> bool:
    low = line.lower()
    return any(token in low for token in ALLOWLIST)


def _is_memory_address(value: str) -> bool:
    """True when ``value`` is nothing but a 32-/64-bit hex memory address."""

    return bool(_MEM_ADDRESS_RE.fullmatch(value.replace("_", "")))


def scan_text(text: str) -> list[tuple[str, int, str]]:
    """Return ``(finding_name, line_number, line_excerpt)`` tuples."""

    hits: list[tuple[str, int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _is_placeholder(line):
            continue
        for name, pattern in PATTERNS.items():
            match = pattern.search(line)
            if match is None:
                continue
            if name in ADDRESS_EXEMPT_TYPES:
                value = match.groupdict().get("value")
                if value and _is_memory_address(value):
                    continue
            hits.append((name, lineno, line.strip()[:120]))
    return hits


def _iter_existing_files(paths: Iterable[str]) -> Iterable[Path]:
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = REPO_ROOT / path
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield path


def main(argv: list[str] | None = None) -> int:
    targets = list(argv if argv is not None else sys.argv[1:])
    total = 0
    for path in _iter_existing_files(targets):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, lineno, excerpt in scan_text(text):
            total += 1
            rel = path.relative_to(REPO_ROOT) if str(path).startswith(str(REPO_ROOT)) else path
            print(f"{rel}:{lineno}: {name}: {excerpt}")
    if total:
        print(f"\nsecret-scan: {total} potential secret(s) found.")
        return 1
    print("secret-scan: clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())