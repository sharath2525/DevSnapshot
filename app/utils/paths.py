"""Local path utilities with Windows-safe behavior."""

from __future__ import annotations

import os
import re
import stat
import sys
from pathlib import Path


_WINDOWS_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def safe_filename_component(value: str, fallback: str = "project") -> str:
    """Sanitize a single filename component for Windows."""

    cleaned = _WINDOWS_INVALID.sub("_", value).strip().rstrip(". ")
    if not cleaned:
        cleaned = fallback
    if cleaned.casefold() in {item.casefold() for item in _WINDOWS_RESERVED}:
        cleaned = f"_{cleaned}"
    return cleaned[:120]


def normalized_path(path: Path) -> str:
    """Return a resolved, case-normalized path string for comparisons."""

    return os.path.normcase(str(path.resolve(strict=False)))


def paths_are_same(first: Path, second: Path) -> bool:
    return normalized_path(first) == normalized_path(second)


def is_path_within(child: Path, parent: Path, *, allow_equal: bool = True) -> bool:
    """Return whether child is contained by parent without requiring existence."""

    child_text = normalized_path(child)
    parent_text = normalized_path(parent)
    try:
        common = os.path.commonpath((child_text, parent_text))
    except ValueError:
        return False
    if common != parent_text:
        return False
    return allow_equal or child_text != parent_text


def is_hidden(path: Path) -> bool:
    """Recognize dot-prefixed and Windows hidden filesystem entries."""

    if path.name.startswith("."):
        return True
    try:
        attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 2))
    except OSError:
        return False


def resource_path(relative_path: str) -> Path:
    """Resolve a development or PyInstaller-bundled resource path."""

    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return bundle_root / relative_path
