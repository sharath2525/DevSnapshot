"""Local JSON configuration for DevSnapshot."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .exclusions import (
    DEFAULT_EXCLUDED_FOLDERS,
    LEGACY_DEFAULT_EXCLUDED_FOLDERS,
    normalize_exclusion,
)


CURRENT_CONFIG_VERSION = 2


@dataclass(slots=True)
class AppConfig:
    """User preferences that are safe to persist locally."""

    config_version: int = CURRENT_CONFIG_VERSION
    project_path: str = ""
    backup_path: str = ""
    snapshot_mode: str = "complete"
    include_git: bool = True
    include_hidden: bool = True
    include_env: bool = True
    excluded_folders: list[str] = field(
        default_factory=lambda: list(DEFAULT_EXCLUDED_FOLDERS)
    )

    @classmethod
    def from_dict(cls, data: object) -> "AppConfig":
        """Load recognized, correctly typed values and ignore unknown keys."""

        if not isinstance(data, dict):
            return cls()

        config = cls()
        version = data.get("config_version")
        if isinstance(version, int) and not isinstance(version, bool):
            config.config_version = version
        if isinstance(data.get("project_path"), str):
            config.project_path = data["project_path"]
        if isinstance(data.get("backup_path"), str):
            config.backup_path = data["backup_path"]
        for key in ("include_git", "include_hidden", "include_env"):
            if isinstance(data.get(key), bool):
                setattr(config, key, data[key])

        exclusions = data.get("excluded_folders")
        if isinstance(exclusions, list):
            cleaned = []
            seen: set[str] = set()
            for item in exclusions:
                if not isinstance(item, str):
                    continue
                normalized = normalize_exclusion(item)
                if normalized and normalized.casefold() not in seen:
                    cleaned.append(normalized)
                    seen.add(normalized.casefold())
            config.excluded_folders = cleaned

        mode = data.get("snapshot_mode")
        if mode in {"complete", "custom"}:
            config.snapshot_mode = mode

        # Version 1 shipped with a large default exclusion list. If it is still
        # unchanged, migrate it to the safer and simpler Complete snapshot.
        is_legacy = not isinstance(version, int) or isinstance(version, bool) or version < 2
        legacy_rules = {value.casefold() for value in LEGACY_DEFAULT_EXCLUDED_FOLDERS}
        loaded_rules = {value.casefold() for value in config.excluded_folders}
        if is_legacy and loaded_rules == legacy_rules:
            config.snapshot_mode = "complete"
            config.include_git = True
            config.include_hidden = True
            config.include_env = True
            config.excluded_folders = []
        elif is_legacy and (
            config.excluded_folders
            or not config.include_git
            or not config.include_hidden
            or not config.include_env
        ):
            config.snapshot_mode = "custom"

        config.config_version = CURRENT_CONFIG_VERSION
        if config.snapshot_mode == "complete":
            config.include_git = True
            config.include_hidden = True
            config.include_env = True
            config.excluded_folders = []
        return config


class ConfigManager:
    """Read and atomically write the application configuration file."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or self.default_config_path()

    @staticmethod
    def default_config_path() -> Path:
        app_data = os.environ.get("APPDATA")
        base = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
        return base / "DevSnapshot" / "config.json"

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            return AppConfig()
        try:
            with self.config_path.open("r", encoding="utf-8") as handle:
                data: Any = json.load(handle)
        except (OSError, json.JSONDecodeError, UnicodeError):
            return AppConfig()
        return AppConfig.from_dict(data)

    def save(self, config: AppConfig) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.config_path.with_suffix(".tmp")
        try:
            with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(asdict(config), handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            temporary_path.replace(self.config_path)
        finally:
            if temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    pass
