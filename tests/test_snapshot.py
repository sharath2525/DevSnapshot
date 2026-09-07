from __future__ import annotations

import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path

from app.core.exclusions import LEGACY_DEFAULT_EXCLUDED_FOLDERS
from app.core.snapshot import SnapshotEngine, SnapshotOptions


class SnapshotEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "demo-project"
        self.backup = self.root / "snapshots"
        self.project.mkdir()
        self.backup.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str = "content") -> Path:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def engine(self, **overrides) -> SnapshotEngine:
        values = {
            "project_path": self.project,
            "backup_path": self.backup,
            "excluded_directories": (),
            "include_git": True,
            "include_hidden": True,
            "include_env": True,
        }
        values.update(overrides)
        return SnapshotEngine(SnapshotOptions(**values))

    @staticmethod
    def names(result) -> set[str]:
        assert result.output_file is not None
        with zipfile.ZipFile(result.output_file) as archive:
            return set(archive.namelist())

    def test_normal_backup_includes_sensitive_and_project_metadata(self) -> None:
        self.write("main.py", "print('hello')")
        self.write(".env", "TOKEN=local-only")
        self.write(".env.production", "MODE=production")
        self.write(".gitignore", ".venv\n")
        self.write(".git/HEAD", "ref: refs/heads/main")
        self.write("config/settings.json", "{}")

        result = self.engine().create_snapshot()

        self.assertTrue(result.success, result.error)
        self.assertTrue(result.verified)
        self.assertEqual(result.file_count, 6)
        self.assertEqual(
            self.names(result),
            {
                "main.py",
                ".env",
                ".env.production",
                ".gitignore",
                ".git/HEAD",
                "config/settings.json",
            },
        )

    def test_complete_snapshot_includes_dependency_and_build_directories(self) -> None:
        self.write("keep.py")
        self.write("node_modules/library/index.js")
        self.write(".venv/Lib/site.py")
        self.write("dist/app.exe")
        self.write("src/__pycache__/module.pyc")

        result = self.engine().create_snapshot()

        self.assertTrue(result.success, result.error)
        self.assertEqual(
            self.names(result),
            {
                "keep.py",
                "node_modules/library/index.js",
                ".venv/Lib/site.py",
                "dist/app.exe",
                "src/__pycache__/module.pyc",
            },
        )

    def test_legacy_exclusions_remain_available_as_custom_rules(self) -> None:
        self.write("keep.py")
        self.write("node_modules/library/index.js")
        self.write("dist/app.exe")

        result = self.engine(
            excluded_directories=LEGACY_DEFAULT_EXCLUDED_FOLDERS
        ).create_snapshot()

        self.assertEqual(self.names(result), {"keep.py"})

    def test_hidden_and_env_options_are_independent(self) -> None:
        self.write("visible.txt")
        self.write(".hidden")
        self.write(".gitignore")
        self.write(".env", "LOCAL=true")
        self.write(".git/HEAD")

        result = self.engine(include_hidden=False, include_env=True).create_snapshot()

        self.assertTrue(result.success, result.error)
        self.assertEqual(self.names(result), {"visible.txt", ".env", ".git/HEAD"})

    def test_env_files_can_be_disabled(self) -> None:
        self.write(".env")
        self.write(".env.local")
        self.write("source.py")
        result = self.engine(include_env=False).create_snapshot()
        self.assertEqual(self.names(result), {"source.py"})

    def test_git_folder_can_be_disabled(self) -> None:
        self.write(".git/HEAD")
        self.write("source.py")
        result = self.engine(include_git=False).create_snapshot()
        self.assertEqual(self.names(result), {"source.py"})

    def test_custom_name_and_relative_path_exclusions(self) -> None:
        self.write("downloads/archive.bin")
        self.write("nested/downloads/file.bin")
        self.write("dataset/raw/huge.bin")
        self.write("other/raw/keep.bin")
        options = ("downloads", "dataset/raw")

        result = self.engine(excluded_directories=options).create_snapshot()

        self.assertTrue(result.success, result.error)
        self.assertEqual(self.names(result), {"other/raw/keep.bin"})

    def test_nested_folder_structure_is_preserved(self) -> None:
        self.write("src/features/snapshot/service.py")
        result = self.engine().create_snapshot()
        self.assertEqual(self.names(result), {"src/features/snapshot/service.py"})

    def test_backup_directory_inside_project_is_automatically_excluded(self) -> None:
        self.backup = self.project / "backups"
        self.backup.mkdir()
        (self.backup / "older.zip").write_bytes(b"old backup")
        self.write("source.py")

        result = self.engine().create_snapshot()

        self.assertTrue(result.success, result.error)
        self.assertEqual(self.names(result), {"source.py"})
        self.assertNotIn("backups/older.zip", self.names(result))

    def test_duplicate_filename_uses_numeric_suffix(self) -> None:
        self.write("source.py")
        moment = datetime(2026, 9, 7, 19, 42, 31)
        first = self.engine().create_snapshot(timestamp=moment)
        second = self.engine().create_snapshot(timestamp=moment)

        self.assertEqual(first.output_file.name, "demo-project_2026-09-07_19-42-31.zip")
        self.assertEqual(second.output_file.name, "demo-project_2026-09-07_19-42-31_2.zip")

    def test_zip_integrity_verification(self) -> None:
        self.write("source.py")
        result = self.engine().create_snapshot()
        self.assertTrue(SnapshotEngine.verify_snapshot(result.output_file)[0])

        corrupt = self.backup / "corrupt.zip"
        corrupt.write_bytes(b"this is not a zip file")
        self.assertFalse(SnapshotEngine.verify_snapshot(corrupt)[0])

    def test_cancelled_snapshot_removes_partial_zip(self) -> None:
        self.write("one.txt", "1" * 20_000)
        self.write("two.txt", "2" * 20_000)
        engine = self.engine()

        def cancel_after_first(current: int, total: int, path: str) -> None:
            del total, path
            if current == 1:
                engine.cancel()

        result = engine.create_snapshot(progress_callback=cancel_after_first)

        self.assertTrue(result.cancelled)
        self.assertFalse(result.success)
        self.assertEqual(list(self.backup.glob("*.zip")), [])

    def test_project_files_are_never_modified(self) -> None:
        source = self.write("source.py", "original")
        before = (source.read_bytes(), source.stat().st_mtime_ns)
        result = self.engine().create_snapshot()
        after = (source.read_bytes(), source.stat().st_mtime_ns)
        self.assertTrue(result.success, result.error)
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
