"""Directory exclusion rules used while scanning a project."""

from __future__ import annotations

from pathlib import PurePath, PurePosixPath
from typing import Iterable


DEFAULT_EXCLUDED_FOLDERS: tuple[str, ...] = ()

# Kept only to migrate installations created before Complete snapshots became
# the default. These entries are never silently applied to a new installation.
LEGACY_DEFAULT_EXCLUDED_FOLDERS: tuple[str, ...] = (
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
    ".gradle",
    ".idea/system",
    "coverage",
)

SUGGESTED_EXCLUDED_FOLDERS: tuple[str, ...] = (
    "node_modules",
    ".venv",
    "dist",
    "build",
)


def normalize_exclusion(value: str) -> str:
    """Return a stable project-relative exclusion rule."""

    normalized = value.strip().replace("\\", "/").strip("/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    if normalized in {"", "."}:
        return ""
    parts = PurePosixPath(normalized).parts
    if any(part in {".", ".."} for part in parts):
        return ""
    return "/".join(parts)


class ExclusionMatcher:
    """Match directory names or exact project-relative directory paths."""

    def __init__(self, exclusions: Iterable[str]) -> None:
        unique: dict[str, str] = {}
        for value in exclusions:
            normalized = normalize_exclusion(str(value))
            if normalized:
                unique.setdefault(normalized.casefold(), normalized)
        self.rules = tuple(unique.values())

    def should_exclude_directory(self, relative_path: PurePath) -> bool:
        """Return whether a relative directory matches any configured rule."""

        relative = relative_path.as_posix().strip("/")
        relative_folded = relative.casefold()
        parts = tuple(part.casefold() for part in relative_path.parts)

        for rule in self.rules:
            rule_folded = rule.casefold()
            if "/" in rule:
                if relative_folded == rule_folded or relative_folded.startswith(
                    f"{rule_folded}/"
                ):
                    return True
            elif rule_folded in parts:
                return True
        return False
