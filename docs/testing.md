# Testing

This repo uses `pytest` for backend tests and `coverage.py` (via `pytest-cov`) for coverage reporting.

## Prerequisites

Run tests inside a Python virtual environment with dependencies installed.

- Create and activate a virtual environment (recommended name: `.venv`):
  - Windows (PowerShell):
    - `python -m venv .venv`
    - `./.venv/Scripts/Activate.ps1`
    - If PowerShell blocks activation with an execution policy error (e.g. “running scripts is disabled…”), you can allow scripts for the *current shell session only*:
      - `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`
      - Then re-run `./.venv/Scripts/Activate.ps1`
  - macOS/Linux (bash/zsh):
    - `python3 -m venv .venv`
    - `source .venv/bin/activate`

- Install dependencies (includes `pytest` and `pytest-cov`):
  - `python -m pip install -r requirements.txt`

## Backend tests

From the repo root:

- Run all backend tests:
  - `python -m pytest`

- Quiet output:
  - `python -m pytest -q`

### Where tests live

- Tests are under `backend/app/tests/`.
- Test discovery is configured in `pytest.ini` via `testpaths = backend/app/tests`.

### Import path behavior

`backend/app/tests/conftest.py` adds `backend/` to `sys.path` so imports like `from app...` resolve correctly when running tests from the repo root.

## Coverage

Coverage configuration lives in `.coveragerc`.

Note: `coverage.py` and `pytest-cov` auto-discover `.coveragerc` by default. A file named `coveragerc` (no leading dot) will be ignored unless you explicitly pass `--cov-config coveragerc`.

Key behaviors configured there:
- Measures **branch coverage** (`branch = True`).
- Treats `backend/app` as the source root (`source = backend/app`).
- Omits boilerplate and non-target files like `__init__.py`, tests, and some infrastructure/mocks.
- Hides fully-covered files in the terminal report (`skip_covered = True`) to reduce noise.

### Run tests with coverage

From the repo root:

- Terminal report (missing lines shown):
  - `python -m pytest --cov --cov-report=term-missing`

- If you want to use a non-default config filename (e.g. `coveragerc`):
  - `python -m pytest --cov --cov-report=term-missing --cov-config=coveragerc`

- Generate an HTML report in `htmlcov/`:
  - `python -m pytest --cov --cov-report=html`
  - Then open `htmlcov/index.html` in a browser.

- Generate a Cobertura-style XML report (`coverage.xml`) (useful for CI):
  - `python -m pytest --cov --cov-report=xml`

### Notes on generated coverage files

- `.coveragerc` is config and should be committed.
- `.coverage` is a generated local database and should **not** be committed (it is already ignored by `.gitignore`).
- `coverage.xml` is usually treated as a CI artifact rather than committed to git.
