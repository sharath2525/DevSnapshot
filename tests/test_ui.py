from __future__ import annotations

import logging
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from app.core.config import AppConfig, ConfigManager
from app.ui.main_window import MainWindow
from app.ui.settings_dialog import SettingsDialog


class MainWindowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_main_window_creates_verified_snapshot_in_worker_thread(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "sample-project"
            backup = root / "snapshots"
            project.mkdir()
            backup.mkdir()
            (project / "main.py").write_text("print('ok')\n", encoding="utf-8")
            (project / ".env").write_text("LOCAL_ONLY=true\n", encoding="utf-8")

            config = AppConfig(
                project_path=str(project),
                backup_path=str(backup),
            )
            logger = logging.getLogger("devsnapshot.ui-test")
            logger.addHandler(logging.NullHandler())
            window = MainWindow(
                config,
                ConfigManager(root / "config.json"),
                logger,
            )

            window._start_snapshot()
            self.assertIsNotNone(window._thread)

            event_loop = QEventLoop()
            timed_out = False

            def fail_on_timeout() -> None:
                nonlocal timed_out
                timed_out = True
                event_loop.quit()

            timeout = QTimer()
            timeout.setSingleShot(True)
            timeout.timeout.connect(fail_on_timeout)
            window._thread.finished.connect(event_loop.quit)
            timeout.start(10_000)
            event_loop.exec()
            timeout.stop()
            self.application.processEvents()

            self.assertFalse(timed_out, "Snapshot worker did not finish within 10 seconds")
            archives = list(backup.glob("*.zip"))
            self.assertEqual(len(archives), 1)
            with zipfile.ZipFile(archives[0]) as archive:
                self.assertEqual(set(archive.namelist()), {"main.py", ".env"})
                self.assertIsNone(archive.testzip())
            self.assertIn("successfully", window.status_label.text().casefold())
            self.assertIsNone(window._thread)
            window.close()

    def test_settings_save_commits_pending_exclusion_and_checkbox_changes(self) -> None:
        config = AppConfig(
            snapshot_mode="custom",
            include_git=False,
            include_hidden=False,
            include_env=False,
            excluded_folders=["dist"],
        )
        dialog = SettingsDialog(config)
        dialog.include_git.setChecked(True)
        dialog.include_hidden.setChecked(True)
        dialog.include_env.setChecked(True)
        dialog.exclusion_input.setText("dataset/raw")

        dialog._save_and_accept()
        dialog.apply_to(config)

        self.assertTrue(config.include_git)
        self.assertTrue(config.include_hidden)
        self.assertTrue(config.include_env)
        self.assertEqual(config.snapshot_mode, "custom")
        self.assertEqual(config.excluded_folders, ["dist", "dataset/raw"])

    def test_complete_mode_clears_all_exclusions(self) -> None:
        config = AppConfig(
            snapshot_mode="custom",
            include_git=False,
            include_hidden=False,
            include_env=False,
            excluded_folders=["node_modules", "dist"],
        )
        dialog = SettingsDialog(config)
        dialog.complete_mode.setChecked(True)
        dialog.apply_to(config)

        self.assertEqual(config.snapshot_mode, "complete")
        self.assertTrue(config.include_git)
        self.assertTrue(config.include_hidden)
        self.assertTrue(config.include_env)
        self.assertEqual(config.excluded_folders, [])

    def test_snapshot_modes_are_exclusive_and_dialog_size_is_stable(self) -> None:
        dialog = SettingsDialog(AppConfig())
        original_size = dialog.size()

        self.assertTrue(dialog.complete_mode.isChecked())
        self.assertFalse(dialog.custom_mode.isChecked())
        dialog.custom_mode.setChecked(True)
        self.application.processEvents()

        self.assertFalse(dialog.complete_mode.isChecked())
        self.assertTrue(dialog.custom_mode.isChecked())
        self.assertEqual(dialog.size(), original_size)

        dialog.complete_mode.setChecked(True)
        self.application.processEvents()
        self.assertTrue(dialog.complete_mode.isChecked())
        self.assertFalse(dialog.custom_mode.isChecked())
        self.assertEqual(dialog.size(), original_size)


if __name__ == "__main__":
    unittest.main()
