# Contributing to DevSnapshot

Thanks for helping improve DevSnapshot. Keep changes focused, local-first, and
safe for project data.

## Development setup

1. Fork and clone the repository.
2. Create a virtual environment: `py -3.12 -m venv .venv`.
3. Activate it: `.venv\Scripts\Activate.ps1`.
4. Install dependencies: `python -m pip install -r requirements.txt`.
5. Run the tests: `python -m unittest discover -s tests -v`.

## Pull requests

- Open an issue first for broad behavior or UI changes.
- Add or update tests for every bug fix and behavior change.
- Never add telemetry, analytics, network access, or source-content logging.
- Do not weaken archive verification, path validation, or partial-ZIP cleanup.
- Keep the interface usable at Windows display scaling between 100% and 200%.
- Run `build.bat` before requesting review when packaging code changes.

By contributing, you agree that your contribution is licensed under the MIT
License included in this repository.
