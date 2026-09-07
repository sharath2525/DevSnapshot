# DevSnapshot

**Checkpoint your project before AI changes it.**

DevSnapshot is a small Windows desktop utility that creates a complete, local ZIP
checkpoint of a development project. It is designed for the moment before a coding
assistant, refactor, migration, or other broad change touches many files.

DevSnapshot is 100% local and offline. It has no account, API, cloud service,
telemetry, analytics, ads, update checker, or network code.

## Why DevSnapshot?

Git is still strongly recommended. DevSnapshot is not a Git replacement.

Git protects committed history. DevSnapshot adds a simple local project checkpoint,
including files that may not be tracked by Git: `.env` files, machine-specific
configuration, local databases, IDE settings, and other ignored project state.

A typical workflow is:

1. Open DevSnapshot.
2. Select a project and backup destination the first time.
3. Click **Create Snapshot** before asking an AI coding assistant to refactor the project.
4. Let the assistant make its changes.
5. If necessary, manually extract the previous ZIP snapshot.

DevSnapshot deliberately does not offer automatic restore in V1, because restoring
could overwrite active project files.

## Install on Windows

For normal use, download `DevSnapshot-Setup-1.0.0.exe` from GitHub Releases. The
per-user installer does not require administrator access. It adds DevSnapshot to
the Start Menu, Windows Search, Apps > Installed apps, and the standard uninstall
list. A portable `DevSnapshot.exe` is also published for users who do not want to
install it.

## Features

- One-click, verified ZIP snapshots
- Responsive PySide6 interface with scan and file-count progress
- Safe cancellation with incomplete ZIP cleanup
- `.env`, `.gitignore`, hidden files, local configuration, and `.git` included by default
- Complete snapshots include every file and folder by default
- Optional Custom mode with editable folder-name and project-relative exclusions
- Automatic exclusion when the backup destination is inside the project
- Collision-safe names such as `project_2026-09-07_19-42-31_2.zip`
- Recent snapshot history
- Graceful per-file warnings for locked, missing, or inaccessible files
- Local settings and rotating error log under `%APPDATA%\DevSnapshot`
- No symlink traversal and no project file modification

## Complete and Custom snapshots

Complete mode is the recommended default and has no user-defined exclusions. This
keeps a checkpoint faithful to the project on disk, including dependency and build
folders. Custom mode is optional and exposes only the inclusion controls and folder
rules the user chooses to change.

An exclusion with one component, such as `downloads`, matches a folder with that
name at any depth. A relative rule, such as `dataset/raw`, matches only that project
path and its descendants. V1 intentionally does not interpret glob syntax.

## Safety model

Project contents are treated strictly as data. DevSnapshot only reads the selected
project, creates ZIP files in the selected destination, and writes its own settings
and logs under AppData. It never runs project code or scripts and never renames,
deletes, or edits project files.

Symbolic links are skipped instead of followed. ZIP files are streamed from disk, so
entire project files are not loaded into memory. Each completed archive is checked
with Python's ZIP integrity test before success is reported.

If the backup directory is a subfolder of the project, that entire subtree is pruned
from the scan. The project folder itself cannot also be the backup folder.

## Run from source

Requirements:

- Windows 10 or Windows 11
- Python 3.10 or newer

From this directory in PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

All runtime features continue to work when the computer is disconnected from the
internet. Internet access is only needed initially if `pip` must download PySide6 or
PyInstaller.

## Run the tests

The core suite uses only the Python standard library and temporary directories:

```powershell
python -m unittest discover -s tests -v
```

The tests cover complete snapshots, `.env` and `.gitignore` inclusion, custom
exclusions, hidden-file controls, nested paths, `.git` controls, in-project
backup exclusion, collision-safe filenames, integrity verification, configuration
persistence, cancellation cleanup, and source-file immutability.

## Build `DevSnapshot.exe`

Run:

```powershell
.\build.bat
```

The script finds `.venv`, the Windows `py` launcher, or `python`; installs the pinned
dependency ranges; runs the complete offline test suite; and invokes the supplied
PyInstaller spec. The one-file, windowed executable is written to:

```text
dist\DevSnapshot.exe
```

Branding is sourced from `resources\icons\devsnapshot.png` and embedded into both
the application UI and Windows executable during the build.

## Build the Windows installer

Install Inno Setup 6, then run:

```powershell
.\build_release.bat
```

This rebuilds and smoke-tests the portable executable before producing:

```text
dist\installer\DevSnapshot-Setup-1.0.0.exe
```

The installer is per-user, registers the application path, and creates the Start
Menu shortcut that makes DevSnapshot discoverable through Windows Search.

## Publishing a release

GitHub Actions tests and builds every push and pull request. Pushing a semantic
version tag such as `v1.0.0` builds the EXE and installer, generates SHA-256
checksums, and creates the GitHub Release automatically.

```powershell
git tag v1.0.0
git push origin v1.0.0
```

## Local files

- Configuration: `%APPDATA%\DevSnapshot\config.json`
- Log: `%APPDATA%\DevSnapshot\logs\devsnapshot.log`

The configuration contains paths and preferences only. Logs contain application
events, filenames/paths when useful for troubleshooting, and errors. Neither stores
source contents, `.env` contents, passwords, or API keys.

## Project layout

```text
devsnapshot/
├── main.py
├── app/
│   ├── core/       # configuration, exclusions, history, ZIP engine
│   ├── ui/         # first run, dashboard, settings, warning details, theme
│   ├── workers/    # QThread worker
│   └── utils/      # paths and local logging
├── resources/icons/
├── tests/
├── installer/
├── .github/workflows/
├── requirements.txt
├── DevSnapshot.spec
├── build.bat
└── build_release.bat
```

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[PRIVACY.md](PRIVACY.md). DevSnapshot is released under the [MIT License](LICENSE).
