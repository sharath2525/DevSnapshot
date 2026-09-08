from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


class StorePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.manifest_path = cls.root / "store" / "AppxManifest.xml.template"
        cls.manifest_text = cls.manifest_path.read_text(encoding="utf-8")

    def test_manifest_is_well_formed_and_uses_partner_identity_tokens(self) -> None:
        root = ET.fromstring(self.manifest_text)
        namespace = {"f": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}
        identity = root.find("f:Identity", namespace)
        self.assertIsNotNone(identity)
        self.assertEqual("__IDENTITY_NAME__", identity.attrib["Name"])
        self.assertEqual("__PUBLISHER__", identity.attrib["Publisher"])
        self.assertEqual("__VERSION__", identity.attrib["Version"])
        self.assertEqual("x64", identity.attrib["ProcessorArchitecture"])

    def test_manifest_declares_desktop_full_trust_application(self) -> None:
        self.assertIn('Name="Windows.Desktop"', self.manifest_text)
        self.assertIn('Name="runFullTrust"', self.manifest_text)
        self.assertIn('uap10:RuntimeBehavior="packagedClassicApp"', self.manifest_text)
        self.assertIn('Executable="DevSnapshot.exe"', self.manifest_text)

    def test_store_build_is_onedir_and_uses_makeappx(self) -> None:
        spec = (self.root / "DevSnapshotStore.spec").read_text(encoding="utf-8")
        build = (self.root / "build_store.ps1").read_text(encoding="utf-8")
        self.assertIn("exclude_binaries=True", spec)
        self.assertIn("COLLECT(", spec)
        self.assertIn("makeappx.exe", build.casefold())
        self.assertIn('"DevSnapshot_{0}_x64.msix" -f $Version', build)
        self.assertIn("[string]$Version = '1.0.0.0'", build)
        self.assertIn("must be between 0 and 65535", build)
        self.assertIn('"ds-" + [guid]', build)

    def test_store_guidance_and_listing_exist(self) -> None:
        self.assertTrue((self.root / "store" / "README.md").is_file())
        self.assertTrue((self.root / "store" / "LISTING.md").is_file())


if __name__ == "__main__":
    unittest.main()
