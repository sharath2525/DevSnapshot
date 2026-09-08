# Changelog

All notable changes to DevSnapshot are documented here.

The format follows Keep a Changelog and the project uses semantic versioning.

## [Unreleased]

## [1.0.0] - 2026-09-08

### Added

- Complete snapshots that include every project file and folder by default.
- Optional Custom snapshot mode with explicit folder exclusions.
- Verified ZIP creation, cancellation cleanup, and collision-safe filenames.
- Local settings, recent snapshot history, and rotating logs.
- Windows application identity, version metadata, installer, and Start Menu entry.

### Fixed

- Prevented both snapshot modes from being selected simultaneously.
- Kept the settings window geometry stable while changing modes.
- Prevented backup destinations inside a project from being archived recursively.
- Isolated packaged Qt dependencies to prevent `QtGui` DLL load failures.
- Removed the unnecessary installer license-acceptance page that made setup appear blocked.
- Made the no-admin per-user setup path fixed and created Start Menu and desktop shortcuts automatically.
