"""Reliable, local-only ZIP snapshot creation."""

from __future__ import annotations

import errno
import logging
import os
import threading
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePath
from typing import Callable

from app.utils.paths import (
    is_hidden,
    is_path_within,
    paths_are_same,
    safe_filename_component,
)

from .exclusions import ExclusionMatcher


ProgressCallback = Callable[[int, int, str], None]
StatusCallback = Callable[[str], None]


class SnapshotError(Exception):
    """An expected snapshot failure suitable for display to the user."""


class _SnapshotCancelled(Exception):
    pass


@dataclass(slots=True)
class SnapshotOptions:
    project_path: Path
    backup_path: Path
    excluded_directories: tuple[str, ...] = ()
    include_git: bool = True
    include_hidden: bool = True
    include_env: bool = True

    def __post_init__(self) -> None:
        self.project_path = Path(self.project_path)
        self.backup_path = Path(self.backup_path)
        self.excluded_directories = tuple(self.excluded_directories)


@dataclass(slots=True, frozen=True)
class SnapshotWarning:
    path: str
    message: str


@dataclass(slots=True)
class ScanResult:
    files: list[Path] = field(default_factory=list)
    skipped_count: int = 0
    warnings: list[SnapshotWarning] = field(default_factory=list)
    cancelled: bool = False


@dataclass(slots=True)
class SnapshotResult:
    success: bool
    output_file: Path | None = None
    file_count: int = 0
    skipped_count: int = 0
    warnings: list[SnapshotWarning] = field(default_factory=list)
    duration: float = 0.0
    size: int = 0
    verified: bool = False
    cancelled: bool = False
    error: str = ""


class SnapshotEngine:
    """Scan a project and stream its files into a verified ZIP archive."""

    def __init__(
        self, options: SnapshotOptions, logger: logging.Logger | None = None
    ) -> None:
        self.options = options
        self._cancel_event = threading.Event()
        self._logger = logger or logging.getLogger("devsnapshot")

    def cancel(self) -> None:
        """Request cooperative cancellation from any thread."""

        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def validate_paths(self) -> None:
        project = self.options.project_path
        backup = self.options.backup_path
        if not project.exists():
            raise SnapshotError("The selected project folder does not exist.")
        if not project.is_dir():
            raise SnapshotError("The selected project path is not a folder.")
        if project.is_symlink():
            raise SnapshotError("A symbolic link cannot be used as the project folder.")
        if not backup.exists():
            raise SnapshotError("The selected backup folder does not exist.")
        if not backup.is_dir():
            raise SnapshotError("The selected backup path is not a folder.")
        if paths_are_same(project, backup):
            raise SnapshotError(
                "The backup folder cannot be the project folder itself. "
                "Choose a subfolder or a folder outside the project."
            )

    def _backup_relative_path(self) -> Path | None:
        project = self.options.project_path.resolve(strict=False)
        backup = self.options.backup_path.resolve(strict=False)
        if not is_path_within(backup, project, allow_equal=False):
            return None
        try:
            return backup.relative_to(project)
        except ValueError:
            return None

    @staticmethod
    def _env_file(name: str) -> bool:
        folded = name.casefold()
        return folded == ".env" or folded.startswith(".env.")

    @staticmethod
    def _warning(path: PurePath | str, error: BaseException | str) -> SnapshotWarning:
        if isinstance(error, OSError) and error.strerror:
            message = error.strerror
        else:
            message = str(error) or error.__class__.__name__
        return SnapshotWarning(str(path), message)

    def scan_files(self, status_callback: StatusCallback | None = None) -> ScanResult:
        """Return eligible files without following symbolic links."""

        self.validate_paths()
        if status_callback:
            status_callback("Scanning project files...")

        project = self.options.project_path.resolve(strict=False)
        backup_relative = self._backup_relative_path()
        matcher = ExclusionMatcher(self.options.excluded_directories)
        result = ScanResult()
        directories = [project]

        while directories:
            if self.is_cancelled:
                result.cancelled = True
                return result

            current = directories.pop()
            try:
                entries = sorted(os.scandir(current), key=lambda item: item.name.casefold())
            except OSError as exc:
                relative_current = current.relative_to(project)
                if current == project:
                    raise SnapshotError(
                        f"The project folder could not be read: {self._warning('.', exc).message}"
                    ) from None
                result.warnings.append(self._warning(relative_current, exc))
                result.skipped_count += 1
                continue

            child_directories: list[Path] = []
            for entry in entries:
                if self.is_cancelled:
                    result.cancelled = True
                    return result

                path = Path(entry.path)
                relative = path.relative_to(project)
                try:
                    if entry.is_symlink():
                        result.skipped_count += 1
                        continue
                    is_directory = entry.is_dir(follow_symlinks=False)
                    is_file = entry.is_file(follow_symlinks=False)
                except OSError as exc:
                    result.warnings.append(self._warning(relative, exc))
                    result.skipped_count += 1
                    continue

                if is_directory:
                    if backup_relative is not None and (
                        relative == backup_relative or backup_relative in relative.parents
                    ):
                        result.skipped_count += 1
                        continue
                    if relative.name.casefold() == ".git" and not self.options.include_git:
                        result.skipped_count += 1
                        continue
                    if matcher.should_exclude_directory(relative):
                        result.skipped_count += 1
                        continue
                    is_git = relative.name.casefold() == ".git"
                    if not self.options.include_hidden and is_hidden(path) and not is_git:
                        result.skipped_count += 1
                        continue
                    child_directories.append(path)
                elif is_file:
                    is_env = self._env_file(relative.name)
                    if is_env and not self.options.include_env:
                        result.skipped_count += 1
                        continue
                    if (
                        not self.options.include_hidden
                        and is_hidden(path)
                        and not (is_env and self.options.include_env)
                    ):
                        result.skipped_count += 1
                        continue
                    result.files.append(path)
                else:
                    result.skipped_count += 1

            directories.extend(reversed(child_directories))

        return result

    def destination_path(self, timestamp: datetime | None = None) -> Path:
        """Return the next non-conflicting output filename without creating it."""

        moment = timestamp or datetime.now()
        project_name = safe_filename_component(
            self.options.project_path.resolve(strict=False).name
        )
        stem = f"{project_name}_{moment:%Y-%m-%d_%H-%M-%S}"
        candidate = self.options.backup_path / f"{stem}.zip"
        suffix = 2
        while candidate.exists():
            candidate = self.options.backup_path / f"{stem}_{suffix}.zip"
            suffix += 1
        return candidate

    def _open_unique_archive(
        self, timestamp: datetime | None
    ) -> tuple[Path, zipfile.ZipFile]:
        """Open an archive exclusively, retrying if another process wins a race."""

        while True:
            candidate = self.destination_path(timestamp)
            try:
                archive = zipfile.ZipFile(
                    candidate,
                    mode="x",
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=6,
                    allowZip64=True,
                )
                return candidate, archive
            except FileExistsError:
                continue

    @staticmethod
    def _fatal_file_error(error: OSError) -> bool:
        return error.errno in {errno.ENOSPC, errno.EDQUOT, errno.EFBIG}

    @staticmethod
    def verify_snapshot(path: Path) -> tuple[bool, str | None]:
        """Test ZIP structure and CRCs, returning the first bad member if any."""

        try:
            with zipfile.ZipFile(path, "r") as archive:
                bad_member = archive.testzip()
            return bad_member is None, bad_member
        except (OSError, zipfile.BadZipFile, RuntimeError):
            return False, None

    @staticmethod
    def _remove_partial(path: Path | None) -> None:
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def create_snapshot(
        self,
        progress_callback: ProgressCallback | None = None,
        status_callback: StatusCallback | None = None,
        *,
        timestamp: datetime | None = None,
    ) -> SnapshotResult:
        """Create and verify a snapshot, cleaning partial output on failure."""

        started = time.monotonic()
        output_path: Path | None = None
        scan = ScanResult()
        archived_count = 0

        try:
            scan = self.scan_files(status_callback)
            if scan.cancelled or self.is_cancelled:
                raise _SnapshotCancelled

            if status_callback:
                status_callback("Creating snapshot...")

            output_path, archive = self._open_unique_archive(timestamp)
            with archive:
                total = len(scan.files)
                for index, file_path in enumerate(scan.files, start=1):
                    if self.is_cancelled:
                        raise _SnapshotCancelled
                    relative = file_path.relative_to(
                        self.options.project_path.resolve(strict=False)
                    )
                    try:
                        if file_path.is_symlink():
                            scan.skipped_count += 1
                            continue
                        archive.write(file_path, arcname=relative.as_posix())
                        archived_count += 1
                    except OSError as exc:
                        if self._fatal_file_error(exc):
                            raise
                        scan.warnings.append(self._warning(relative, exc))
                        scan.skipped_count += 1
                    except ValueError as exc:
                        scan.warnings.append(self._warning(relative, exc))
                        scan.skipped_count += 1
                    if progress_callback:
                        progress_callback(index, total, relative.as_posix())

            if self.is_cancelled:
                raise _SnapshotCancelled
            if status_callback:
                status_callback("Verifying snapshot...")
            verified, bad_member = self.verify_snapshot(output_path)
            if not verified:
                detail = f" The first damaged file was: {bad_member}." if bad_member else ""
                raise SnapshotError(f"Snapshot verification failed.{detail}")

            size = output_path.stat().st_size
            duration = time.monotonic() - started
            self._logger.info(
                "Snapshot created: %s (%d files, %d bytes)",
                output_path,
                archived_count,
                size,
            )
            return SnapshotResult(
                success=True,
                output_file=output_path,
                file_count=archived_count,
                skipped_count=scan.skipped_count,
                warnings=scan.warnings,
                duration=duration,
                size=size,
                verified=True,
            )
        except _SnapshotCancelled:
            self._remove_partial(output_path)
            self._logger.info("Snapshot cancelled; partial archive removed")
            return SnapshotResult(
                success=False,
                file_count=archived_count,
                skipped_count=scan.skipped_count,
                warnings=scan.warnings,
                duration=time.monotonic() - started,
                cancelled=True,
            )
        except Exception as exc:
            self._remove_partial(output_path)
            if isinstance(exc, SnapshotError):
                message = str(exc)
                self._logger.error("Snapshot failed: %s", message)
            else:
                message = str(exc) or "The snapshot could not be created."
                self._logger.exception("Snapshot failed")
            return SnapshotResult(
                success=False,
                file_count=archived_count,
                skipped_count=scan.skipped_count,
                warnings=scan.warnings,
                duration=time.monotonic() - started,
                error=message,
            )
