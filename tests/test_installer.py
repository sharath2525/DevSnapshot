from pathlib import Path
import unittest


class InstallerDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        installer_path = Path(__file__).resolve().parents[1] / "installer" / "DevSnapshot.iss"
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


if __name__ == "__main__":
    unittest.main()
