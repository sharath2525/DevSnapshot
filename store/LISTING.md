# DevSnapshot Store listing draft

## Product name

DevSnapshot

## Short description

Create complete, verified local ZIP checkpoints before AI tools or broad code changes modify your project.

## Description

DevSnapshot is a private, offline checkpoint utility built for developers.

Before an AI coding session, refactor, dependency upgrade, or migration, select a
project and create a verified ZIP snapshot with one click. Complete mode captures
the project as it exists on disk, including hidden files, environment files,
dependencies, build output, and local Git metadata. Custom mode lets you skip only
the folders you intentionally exclude.

DevSnapshot works entirely on your PC. It has no account, cloud service, telemetry,
analytics, advertising, or network connection. It never edits or deletes project
files and verifies every completed archive before reporting success.

DevSnapshot complements Git by protecting local and untracked project state. It is
not a replacement for version control.

## Features

- One-click local project checkpoints
- Complete snapshots by default
- Optional custom folder exclusions
- ZIP integrity verification
- Progress reporting and safe cancellation
- Automatic protection against recursive backup folders
- Recent snapshot history
- No account, cloud service, telemetry, or network access
- No modification of project files

## Suggested category

Developer tools; secondary category: Productivity.

## Search terms

project backup, developer tools, code snapshot, zip backup, AI coding, local backup, project checkpoint

## URLs

- Website: the GitHub repository URL
- Support: the GitHub repository Issues URL
- Privacy policy: the public `PRIVACY.md` URL on the GitHub repository

## Certification notes

DevSnapshot is a full-trust desktop utility because users explicitly select local
project and backup folders. It reads project files only to create a ZIP archive in
the selected local destination. It does not execute project files, install drivers
or services, access the network, collect telemetry, require an account, or transmit
data.

Test procedure:

1. Launch DevSnapshot.
2. Select a small local folder as the project.
3. Select a different local folder as the backup destination.
4. Choose Complete snapshot and select Create Snapshot.
5. Confirm the success state and verified ZIP file in the destination.

No special credentials or external dependencies are required.

The package includes the standard CPython 3.12 and Qt 6 runtimes. The Windows App
Certification Kit's optional blocked-executable heuristic can report process-launch
APIs and short text matches inside those upstream binaries. DevSnapshot does not
run project files or debugging tools. Its only shell launch is the explicit
user-facing action that opens the selected backup folder in Windows Explorer.
