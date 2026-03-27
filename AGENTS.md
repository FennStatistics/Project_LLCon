# AGENTS

Purpose
- This repository contains a legal XML corpus and a small GUI entry point.
- Use this file to guide agentic changes, tooling, and conventions.

Repository layout
- README.md: minimal project marker.
- install_readme.md: dependency install guide for GUI/XML tooling.
- application/main.py: PySide6 GUI entry point.
- data/Wendel_Korpus_BVerfG/: main corpus assets (PDFs, XML, CSV, CSS).
- data/Wendel_Korpus_BVerfG/info/: CSV metadata tables.
- data/Wendel_Korpus_BVerfG/xml/: XML source files.

Build, lint, test
- No build system detected.
- No lint configuration detected.
- No test framework detected.
- There are no commands to run a single test.
- If you add code, also add and document its build/lint/test commands here.

Run app (current)
- `python application/main.py`

Dependencies
- See `install_readme.md` for required Python packages.
- There is no requirements.txt or pyproject.toml in this repo.

Working assumptions for new code
- Prefer Python 3 for data tooling unless project requirements say otherwise.
- Keep tooling optional and separate from the corpus data.
- Do not introduce heavyweight dependencies unless clearly justified.
- Preserve existing UI approach (PySide6/Qt).

Code style guidelines (general)
- Follow existing conventions in any new code you add.
- Keep functions small and single purpose.
- Favor pure functions where possible; isolate I/O at boundaries.
- Use explicit, descriptive names; avoid abbreviations.
- Avoid magic numbers; introduce named constants.
- Avoid global state; pass configuration explicitly.

Imports
- Order imports: standard library, third-party, local.
- Use one import per line; avoid wildcard imports.
- Prefer absolute imports over relative unless package layout requires.

Formatting
- Use consistent indentation (4 spaces for Python).
- Keep lines <= 88 characters for Python; wrap long lines.
- Use f-strings for interpolation in Python 3.
- Avoid trailing whitespace.

Types
- Use type hints for public functions and data structures.
- Prefer built-in generics (list[str], dict[str, int]) on Python 3.9+.
- Use dataclasses for simple structured records.
- Validate external data at boundaries; do not assume schema.

Naming conventions
- Variables and functions: snake_case.
- Classes: PascalCase.
- Constants: UPPER_CASE.
- Files and folders: lowercase with underscores if needed.

Error handling
- Fail fast on invalid inputs; include actionable error messages.
- Use exceptions for error cases; avoid silent failures.
- Wrap I/O with clear context in error messages.
- Do not catch Exception broadly unless re-raising with context.

Logging and CLI behavior
- Use standard logging (logging module) instead of print for tools.
- Provide a quiet default and a verbose flag for diagnostics.
- Exit non-zero on errors.

PySide6/UI guidelines
- Keep UI creation in functions/classes; avoid module-level side effects.
- Use `if __name__ == "__main__":` for app entry points.
- Keep long-running work off the UI thread.
- Separate UI wiring from data parsing logic.

Data handling
- Treat data/ as source of truth; avoid in-place edits.
- If transformation is needed, write outputs to a new directory.
- Preserve original encodings and line endings.
- Avoid normalizing or reformatting corpus XML unless required.
- Document any data changes with clear scripts and outputs.

CSV handling
- Use utf-8 encoding unless headers indicate otherwise.
- Preserve delimiter and quoting style.
- Do not reorder columns without a strong reason.
- Keep headers intact; do not rename without documentation.

XML handling
- Preserve namespaces and attribute order when possible.
- Avoid pretty-printing if it changes whitespace semantics.
- Validate well-formedness after edits.

PDF handling
- Treat PDFs as immutable artifacts.
- If extraction is needed, store derived text separately.

Paths and file access
- Use pathlib.Path for paths.
- Avoid hardcoded absolute paths.
- Assume the workspace root is the current working directory.

Performance
- Stream large files; do not load full corpus into memory.
- Use generators/iterators for large XML and CSV.
- Avoid quadratic algorithms on corpus-sized data.

Testing guidelines (if you add code)
- Add unit tests alongside new logic.
- Prefer pytest for Python tests.
- Keep tests deterministic; avoid network calls.
- Use small fixtures; avoid copying large corpus files into tests.

Single-test usage (if you add pytest)
- Run one test file: `pytest path/to/test_file.py`.
- Run one test case: `pytest path/to/test_file.py -k test_name`.

Linting/formatting (if you add tooling)
- Prefer ruff for linting and formatting.
- Example lint: `ruff check .`.
- Example format: `ruff format .`.

Packaging (if you add it)
- Use PyInstaller for Windows exe builds.
- Document the exact PyInstaller command used.

Documentation
- Update README.md if you add tooling or scripts.
- Keep AGENTS.md in sync with new commands.

Cursor/Copilot rules
- No .cursor/rules/ directory found.
- No .cursorrules file found.
- No .github/copilot-instructions.md found.

Security and privacy
- Do not add credentials or secrets to the repository.
- Avoid embedding external URLs unless necessary.
- Validate any new dependencies for licensing and security.

Change management
- Minimize diffs in data files.
- Prefer additive changes; avoid destructive edits.
- Document rationale for any data modifications.

Output locations
- Put generated outputs under a new top-level `outputs/` or `derived/` directory.
- Include a README in output directories describing provenance.

File naming for outputs
- Use ISO dates (YYYY-MM-DD) in output filenames.
- Include a short descriptor and version if needed.

Reproducibility
- Provide a single entry script for reproducible pipelines.
- Capture parameters and versions in a sidecar metadata file.

Questions to resolve before large changes
- Confirm desired language/tooling.
- Confirm whether corpus data can be modified in place.
- Confirm licensing requirements for derived outputs.
