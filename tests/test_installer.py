from pathlib import Path
import unittest


class InstallerDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        installer_path = cls.root / "installer" / "DevSnapshot.iss"
        cls.installer = installer_path.read_text(encoding="utf-8").lower()

    def test_installer_is_per_user_and_does_not_require_license_acceptance(self) -> None:
        self.assertIn("privilegesrequired=lowest", self.installer)
        self.assertIn(r"defaultdirname={localappdata}\programs\{#myappname}", self.installer)
        self.assertNotIn("licensefile=", self.installer)

    def test_start_menu_and_desktop_shortcuts_are_always_created(self) -> None:
        shortcut_lines = [
            line.strip()
            for line in self.installer.splitlines()
            if line.strip().startswith("name:")
        ]
        start_menu = [line for line in shortcut_lines if "{autoprograms}" in line]
        desktop = [line for line in shortcut_lines if "{autodesktop}" in line]

        self.assertEqual(1, len(start_menu))
        self.assertEqual(1, len(desktop))
        self.assertNotIn("tasks:", desktop[0])

    def test_open_source_documents_are_installed(self) -> None:
        for document in ("license", "readme.md", "privacy.md"):
            with self.subTest(document=document):
                self.assertIn(f'source: "..\\{document}"', self.installer)

    def test_readme_uses_stable_latest_release_download(self) -> None:
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        direct_download = (
            "https://github.com/sharath2525/DevSnapshot/"
            "releases/latest/download/DevSnapshot-Setup.exe"
        )
        self.assertIn(direct_download, readme)

    def test_release_publishes_stable_installer_name(self) -> None:
        workflow = (self.root / ".github" / "workflows" / "release.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('"dist/DevSnapshot-Setup.exe"', workflow)
        self.assertIn("Copy-Item", workflow)

    def test_ci_runs_on_repository_default_branch(self) -> None:
        workflow = (self.root / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("branches: [master, main]", workflow)


if __name__ == "__main__":
    unittest.main()
