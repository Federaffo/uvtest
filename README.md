# uvtest

A CLI tool to run pytest tests across all packages in a UV monorepo.

## Features

- **Automatic Package Discovery**: Finds all packages with `pyproject.toml` in your monorepo
- **Isolated Mode (Default)**: Fresh ephemeral environments for hermetic CI runs
- **Sync Mode**: Cached venv for faster local development
- **Package Filtering**: Test specific packages with glob patterns (`-p`)
- **Pytest Passthrough**: Pass arguments to pytest with `--` separator
- **Coverage Support**: Generate coverage reports with `uvtest coverage`

## Installation

```bash
uv tool install uvtest
```

Or run directly:

```bash
uv add uvtest
uv run uvtest
```

## Usage

### Quick Start

```bash
uvtest scan                           # List packages with tests
uvtest run                            # Run all tests (isolated mode)
uvtest run --sync                     # Sync mode (faster locally)
uvtest run -v                         # Verbose output
uvtest run -vv                        # Full pytest output
uvtest run --fail-fast                # Stop on first failure
uvtest run -p "core-*"                # Filter packages
uvtest run -- -k test_foo -x          # Pass args to pytest
uvtest coverage                       # Run with coverage
```

### Commands

#### `uvtest scan`

List all packages with tests in the monorepo.

```
package-api   ./packages/api
package-core  ./packages/core

2 packages with tests found.
```

#### `uvtest run [OPTIONS] [-- PYTEST_ARGS...]`

Run tests across all packages.

**Options:**
- `-v, --verbose`: Show progress (`-vv` for full pytest output)
- `--fail-fast`: Stop on first failure
- `--sync`: Use sync mode instead of isolated mode
- `-p, --package PATTERN`: Filter packages (supports globs, repeatable)

**Execution Modes:**
- **Isolated (default)**: Fresh environment per package. Best for CI.
- **Sync (`--sync`)**: Runs `uv sync`, reuses `.venv`. Faster for local dev.

#### `uvtest coverage [OPTIONS] [-- PYTEST_ARGS...]`

Run tests with coverage. Same options as `run`.

Automatically detects source directory and adds `pytest-cov` in isolated mode.

### Global Options

- `--version`: Show version
- `--help`: Show help

## Monorepo Structure

```
my-monorepo/
├── pyproject.toml              # Root (excluded)
├── packages/
│   ├── api/
│   │   ├── pyproject.toml
│   │   └── tests/              # ← Will be tested
│   └── utils/
│       ├── pyproject.toml
│       └── src/                # No tests/, skipped
└── .venv/
```

## CI/CD

```yaml
- name: Run tests
  run: uvtest run --fail-fast

- name: With coverage
  run: uvtest coverage --fail-fast -v
```

**Exit Codes:** `0` = all passed, `1` = failure

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No packages found | Ensure `pyproject.toml` + `tests/` directory exist |
| Filter matches nothing | Check names with `uvtest scan`, quote glob patterns |
| Sync failures | Verify `pyproject.toml`, run `uv sync` manually |
| Tests not running | Check pytest in deps, verify `test_*.py` naming |

## Requirements

- Python 3.10+
- UV package manager
- Pytest in each package's dependencies

## License

[Your License Here]
