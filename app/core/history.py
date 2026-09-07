"""Discover snapshots already present in the selected destination."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.utils.paths import safe_filename_component


@dataclass(slots=True, frozen=True)
class SnapshotInfo:
    path: Path
    size: int
    modified: datetime


def list_recent_snapshots(
    backup_path: Path, project_name: str, limit: int = 5
) -> list[SnapshotInfo]:
    """Return the newest matching ZIP files, ignoring inaccessible entries."""

    if not backup_path.is_dir():
        return []
    prefix = f"{safe_filename_component(project_name)}_"
    snapshots: list[SnapshotInfo] = []
    try:
        candidates = backup_path.iterdir()
        for path in candidates:
            if not path.name.casefold().startswith(prefix.casefold()):
                continue
            if path.suffix.casefold() != ".zip" or not path.is_file():
                continue
            try:
                details = path.stat()
            except OSError:
                continue
            snapshots.append(
                SnapshotInfo(
                    path=path,
                    size=details.st_size,
                    modified=datetime.fromtimestamp(details.st_mtime),
                )
            )
    except OSError:
        return []
    snapshots.sort(key=lambda item: item.modified, reverse=True)
    return snapshots[: max(0, limit)]
