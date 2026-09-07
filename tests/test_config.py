from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.core.config import AppConfig, ConfigManager
from app.core.exclusions import LEGACY_DEFAULT_EXCLUDED_FOLDERS


class ConfigManagerTests(unittest.TestCase):
    def test_configuration_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "settings" / "config.json"
            manager = ConfigManager(path)
            expected = AppConfig(
                project_path=r"C:\Projects\demo",
                backup_path=r"D:\Snapshots",
                snapshot_mode="custom",
                include_git=False,
                include_hidden=False,
                include_env=True,
                excluded_folders=["node_modules", "dataset/raw"],
            )
            manager.save(expected)
            self.assertEqual(manager.load(), expected)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("contents", saved)

    def test_invalid_json_returns_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text("not json", encoding="utf-8")
            loaded = ConfigManager(path).load()
            self.assertTrue(loaded.include_git)
            self.assertTrue(loaded.include_env)
            self.assertEqual(loaded.snapshot_mode, "complete")
            self.assertEqual(loaded.excluded_folders, [])

    def test_unrecognized_and_invalid_values_are_ignored(self) -> None:
        loaded = AppConfig.from_dict(
            {
                "project_path": 42,
                "include_git": "yes",
                "excluded_folders": ["tmp", "TMP", "../outside", 99],
                "secret_file_contents": "must not be retained",
            }
        )
        self.assertEqual(loaded.project_path, "")
        self.assertTrue(loaded.include_git)
        self.assertEqual(loaded.snapshot_mode, "custom")
        self.assertEqual(loaded.excluded_folders, ["tmp"])

    def test_legacy_default_exclusions_migrate_to_complete_snapshot(self) -> None:
        loaded = AppConfig.from_dict(
            {
                "include_git": False,
                "include_hidden": False,
                "include_env": False,
                "excluded_folders": list(LEGACY_DEFAULT_EXCLUDED_FOLDERS),
            }
        )
        self.assertEqual(loaded.snapshot_mode, "complete")
        self.assertTrue(loaded.include_git)
        self.assertTrue(loaded.include_hidden)
        self.assertTrue(loaded.include_env)
        self.assertEqual(loaded.excluded_folders, [])


if __name__ == "__main__":
    unittest.main()
