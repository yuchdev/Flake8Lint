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
        ".eggs",
        "eggs",
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
    root_dir = _root_dir(effective_config)
    seen: set[Path] = set()
    results: list[Path] = []

    for raw_path in paths:
        path = _resolve_candidate_path(raw_path, root_dir)
        if path.is_file():
            resolved = path.resolve()
            if _is_python_file(resolved) and _path_allowed(resolved, effective_config):
                if resolved not in seen:
                    seen.add(resolved)
                    results.append(resolved)
            continue

        if not path.exists():
            continue

        for file_path in _iter_directory(path.resolve(), effective_config):
            if _path_allowed(file_path, effective_config) and file_path not in seen:
                seen.add(file_path)
                results.append(file_path)

    return tuple(sorted(results))


def _iter_directory(path: Path, config: LintConfig) -> Iterable[Path]:
    root_dir = _root_dir(config)
    for root, dirnames, filenames in os.walk(path):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in DEFAULT_EXCLUDED_DIR_NAMES
            and not _path_matches_any(Path(root) / name, config.exclude, root_dir)
        )
        root_path = Path(root)
        for filename in sorted(filenames):
            candidate = root_path / filename
            if _is_python_file(candidate):
                yield candidate.resolve()


def _is_python_file(path: Path) -> bool:
    return path.suffix == ".py"


def _path_allowed(path: Path, config: LintConfig) -> bool:
    root_dir = _root_dir(config)
    if _is_under_default_excluded_dir(path, root_dir):
        return False
    if config.include and not _path_matches_any(path, config.include, root_dir):
        return False
    if _path_matches_any(path, config.exclude, root_dir):
        return False
    return True


def path_matches_any(
    path: str | Path,
    patterns: Iterable[str],
    root_dir: str | Path | None,
) -> bool:
    candidate = Path(path).resolve()
    return _path_matches_any(candidate, patterns, Path(root_dir).resolve() if root_dir else None)


def _path_matches_any(path: Path, patterns: Iterable[str], root_dir: Path | None) -> bool:
    relative = _relative_path(path, root_dir)
    name = path.name
    for pattern in patterns:
        normalized = pattern.replace("\\", "/").rstrip("/")
        if not normalized:
            continue
        if _is_recursive_directory_match(relative, normalized):
            return True
        if fnmatch(relative, normalized) or fnmatch(name, normalized):
            return True
    return False


def _is_recursive_directory_match(relative: str, pattern: str) -> bool:
    return relative == pattern or relative.startswith(f"{pattern}/")


def _relative_path(path: Path, root_dir: Path | None) -> str:
    if root_dir is not None:
        return os.path.relpath(path.resolve(), root_dir).replace("\\", "/")
    return path.resolve().as_posix()


def _is_under_default_excluded_dir(path: Path, root_dir: Path) -> bool:
    relative_parts = _relative_path(path, root_dir).split("/")
    return any(
        part in DEFAULT_EXCLUDED_DIR_NAMES
        for part in relative_parts
        if part not in {"", ".", ".."}
    )


def _resolve_candidate_path(path: str | Path, root_dir: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return root_dir / candidate


def _root_dir(config: LintConfig) -> Path:
    return (config.base_dir or Path.cwd()).resolve()
