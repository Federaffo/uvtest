# uvtest

A CLI tool to run pytest tests across all packages in a UV monorepo.

## Overview

`uvtest` simplifies testing in UV monorepos by automatically discovering packages, syncing dependencies, and running pytest across all packages with tests. Perfect for CI/CD pipelines and local development workflows.

## Features

- **Automatic Package Discovery**: Finds all packages with `pyproject.toml` in your monorepo
- **Dependency Management**: Runs `uv sync` before testing to ensure dependencies are installed
- **Test Execution**: Runs pytest in each package with tests
- **Flexible Verbosity**: Control output detail with `-v` and `-vv` flags
- **CI/CD Ready**: Proper exit codes and `--fail-fast` option for quick feedback
- **Package Filtering**: Test specific packages with glob pattern matching (coming soon)
- **Coverage Support**: Generate coverage reports (coming soon)

## Installation

Install `uvtest` as a UV tool:

```bash
uv tool install uvtest
```

Or use it directly in your project:

```bash
# Add to pyproject.toml dependencies
uv add uvtest

# Run without installing
uv run uvtest
```

## Usage

### Quick Start

```bash
# Scan for packages with tests
uvtest scan

# Run tests across all packages
uvtest run

# Run with verbose output
uvtest run -v

# Run with very verbose output (shows full pytest output)
uvtest run -vv

# Stop on first failure (fast feedback for CI)
uvtest run --fail-fast
```

### Commands

#### `uvtest scan`

Discover and list all packages with tests in your monorepo.

```bash
uvtest scan
```

**Output:**
```
package-api  ./packages/api
package-core  ./packages/core
package-utils  ./packages/utils

3 packages with tests found.
```

**Behavior:**
- Recursively searches for `pyproject.toml` files in subdirectories
- Only lists packages that have a `tests/` or `test/` directory
- Skips common directories: `.venv`, `node_modules`, `.git`, `__pycache__`, etc.
- Exits with code 1 if no packages with tests are found

---

#### `uvtest run`

Run pytest tests across all packages in the monorepo.

```bash
uvtest run [OPTIONS]
```

**Options:**
- `--fail-fast`: Stop execution after the first package with failing tests
- `-v, --verbose`: Show package names as they complete
- `-vv`: Show full pytest output for each package
- `--help`: Show help message

**Examples:**

```bash
# Run all tests with minimal output
uvtest run

# Run with progress updates
uvtest run -v

# Run with full pytest output
uvtest run -vv

# Stop on first failure (great for CI)
uvtest run --fail-fast

# Combine flags
uvtest run -v --fail-fast
```

**Behavior:**
1. Discovers all packages with tests
2. For each package:
   - Runs `uv sync` to install dependencies
   - Runs `pytest` in the package directory
   - Tracks pass/fail status and duration
3. Displays summary of results
4. Exits with code 0 if all tests pass, 1 if any fail

**Output Modes:**

*Default (minimal):*
```
Test Results:
✓ package-api
✗ package-core
✓ package-utils
```

*Verbose (`-v`):*
```
Testing package-api...
package-api: ✓ PASSED

Testing package-core...
package-core: ✗ FAILED

Testing package-utils...
package-utils: ✓ PASSED
```

*Very Verbose (`-vv`):*
```
Testing package-api...
Sync output:
Resolved 15 packages in 245ms
[full pytest output shown...]
package-api: ✓ PASSED
```

---

### Global Options

Available for all commands:

- `--version`: Show uvtest version
- `-v, --verbose`: Increase verbosity (can be used multiple times: `-v`, `-vv`)
- `--help`: Show help message

## Monorepo Structure

`uvtest` works with monorepos structured like this:

```
my-monorepo/
├── pyproject.toml          # Root project (excluded from testing)
├── packages/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   └── tests/          # ← Has tests, will be tested
│   ├── core/
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   └── tests/          # ← Has tests, will be tested
│   └── utils/
│       ├── pyproject.toml
│       └── src/            # No tests/ dir, skipped
└── .venv/
```

**Requirements:**
- Each package must have a `pyproject.toml` file
- Only packages with a `tests/` or `test/` directory are tested
- The root `pyproject.toml` is excluded from testing

## Exit Codes

`uvtest` uses standard exit codes for CI/CD integration:

- **0**: All tests passed successfully
- **1**: One or more tests failed
- **1**: No packages with tests found
- **1**: Sync failed for one or more packages

## Use Cases

### Local Development

```bash
# Quick check before committing
uvtest run --fail-fast

# Detailed debugging
uvtest run -vv

# See what would be tested
uvtest scan
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: uvtest run --fail-fast
```

Benefits:
- Fast feedback with `--fail-fast`
- Proper exit codes for pipeline failure detection
- Automatic dependency syncing with `uv sync`
- Minimal setup required

## How It Works

1. **Discovery Phase**
   - Recursively searches for `pyproject.toml` files
   - Filters to packages with `tests/` or `test/` directories
   - Excludes common directories (`.venv`, `node_modules`, etc.)

2. **Sync Phase**
   - Runs `uv sync` in each package directory
   - Ensures all dependencies are installed
   - Uses `--quiet` flag unless `-vv` is specified

3. **Test Phase**
   - Runs `uv run pytest` in each package
   - Captures output and exit codes
   - Tracks duration and pass/fail status

4. **Reporting Phase**
   - Displays results based on verbosity level
   - Shows summary of all package results
   - Exits with appropriate code for CI/CD

## Tips & Best Practices

1. **Use `--fail-fast` in CI**: Get faster feedback by stopping on first failure
2. **Use `-v` for debugging**: See which package is failing without overwhelming output
3. **Use `-vv` for deep debugging**: See full pytest output when troubleshooting
4. **Run `uvtest scan` first**: Verify package discovery before running tests
5. **Keep tests isolated**: Each package should have independent tests

## Troubleshooting

### No packages found

```
No packages with tests found.
```

**Solution:**
- Ensure your packages have `pyproject.toml` files
- Ensure packages have a `tests/` or `test/` directory
- Check that you're running from the monorepo root

### Sync failures

```
Failed to sync package-name: [error message]
```

**Solution:**
- Check `pyproject.toml` dependencies are valid
- Ensure `uv` is installed and accessible
- Try running `uv sync` manually in the package directory

### Tests not running

**Solution:**
- Verify pytest is installed in the package dependencies
- Check that test files follow pytest naming conventions (`test_*.py`)
- Run `uv run pytest` manually in the package to verify

## Requirements

- Python 3.10 or higher
- UV package manager installed
- Pytest in each package's dependencies

## Development

```bash
# Clone the repository
git clone <repo-url>
cd uvtest

# Install dependencies
uv sync

# Run tests
uv run pytest tests/

# Run uvtest on itself
uv run uvtest scan
```

## Coming Soon

- **Package Filtering**: `--package` flag to test specific packages
- **Pytest Passthrough**: Pass arguments to pytest with `--`
- **Coverage Reports**: `uvtest coverage` command
- **Summary Tables**: Detailed test result tables
- **Colored Output**: `--no-color` flag for plain output

## License

[Your License Here]

## Contributing

Contributions welcome! Please open an issue or pull request.
