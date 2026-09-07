"""Reusable Python file discovery."""

from __future__ import annotations

import os
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable

from .config import LintConfig

DEFAULT_EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "build",
        "dist",
        ".tox",
        ".nox",
        ".cache",
        ".pytest_cache",
        ".hypothesis",
        ".htmlcov",
        ".idea",
        ".vscode",
        "node_modules",
    }
)


def discover_python_files(
    paths: Iterable[str | Path],
    *,
    config: LintConfig | None = None,
) -> tuple[Path, ...]:
    effective_config = config or LintConfig()
    seen: set[Path] = set()
    results: list[Path] = []

    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file():
            resolved = path.resolve()
            if _is_python_file(resolved) and _path_allowed(resolved, effective_config):
                if resolved not in seen:
                    seen.add(resolved)
                    results.append(resolved)
            continue

        if not path.exists():
            continue

        for file_path in _iter_directory(path.resolve()):
            if _path_allowed(file_path, effective_config) and file_path not in seen:
                seen.add(file_path)
                results.append(file_path)

    return tuple(sorted(results))


def _iter_directory(path: Path) -> Iterable[Path]:
    for root, dirnames, filenames in os.walk(path):
        dirnames[:] = sorted(name for name in dirnames if name not in DEFAULT_EXCLUDED_DIR_NAMES)
        root_path = Path(root)
        for filename in sorted(filenames):
            candidate = root_path / filename
            if _is_python_file(candidate):
                yield candidate.resolve()


def _is_python_file(path: Path) -> bool:
    return path.suffix == ".py"


def _path_allowed(path: Path, config: LintConfig) -> bool:
    absolute = path.as_posix()
    if config.include and not any(_matches(absolute, pattern) for pattern in config.include):
        return False
    if any(_matches(absolute, pattern) for pattern in config.exclude):
        return False
    if any(part in DEFAULT_EXCLUDED_DIR_NAMES for part in path.parts):
        return False
    return True


def _matches(value: str, pattern: str) -> bool:
    return fnmatch(value, pattern) or fnmatch(Path(value).name, pattern)
