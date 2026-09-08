# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH)
logo_path = project_root / "resources" / "icons" / "devsnapshot.png"
legacy_icon_path = project_root / "resources" / "icons" / "devsnapshot.ico"
icon_path = legacy_icon_path if legacy_icon_path.is_file() else logo_path
version_path = project_root / "version_info.txt"
manifest_path = project_root / "windows_app.manifest"
data_files = []
if logo_path.is_file():
    data_files.append((str(logo_path), "resources/icons"))
if legacy_icon_path.is_file():
    data_files.append((str(legacy_icon_path), "resources/icons"))

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=data_files,
    hiddenimports=["PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

# PyInstaller searches every directory on PATH while resolving native DLLs. A
# build launched from an IDE or development tool can therefore accidentally
# collect that tool's private ICU/UCRT libraries instead of using Windows' own
# runtime libraries. Such a mixed bundle builds successfully but fails at
# startup with "DLL load failed while importing QtGui" on a normal desktop.
#
# Keep DLLs shipped by PySide6 itself, but discard Windows-runtime shims and
# anything resolved from Codex's private native dependency directories. The
# build script also sanitizes PATH; this filter is a second line of defence for
# people who invoke PyInstaller directly.
def _is_unsafe_runtime_binary(entry):
    destination, source = str(entry[0]), str(entry[1])
    name = Path(destination).name.casefold()
    source_text = source.replace("\\", "/").casefold()
    comes_from_pyside = "/site-packages/pyside6/" in source_text
    is_windows_runtime_shim = (
        name.startswith("api-ms-win-")
        or name == "ucrtbase.dll"
        or name in {"icu.dll", "icuin.dll", "icuuc.dll"}
        or name.startswith("icudt")
    )
    is_codex_native_dependency = (
        "/codex-runtimes/" in source_text
        and "/dependencies/native/" in source_text
    )
    return is_codex_native_dependency or (
        is_windows_runtime_shim and not comes_from_pyside
    )


a.binaries = [entry for entry in a.binaries if not _is_unsafe_runtime_binary(entry)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DevSnapshot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.is_file() else None,
    version=str(version_path) if version_path.is_file() else None,
    manifest=str(manifest_path),
)
