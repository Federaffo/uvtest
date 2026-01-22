"""Test runner for executing pytest in package directories."""

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TestResult:
    """Result from running tests in a package."""

    package_name: str
    passed: bool
    duration: float
    output: str
    return_code: int


@dataclass
class SyncResult:
    """Result from syncing a package."""

    package_name: str
    success: bool
    output: str
    return_code: int


def sync_package(
    package_path: Path, package_name: str, verbose: bool = False
) -> SyncResult:
    cmd = ["uv", "sync"]
    if not verbose:
        cmd.append("--quiet")

    try:
        result = subprocess.run(
            cmd,
            cwd=package_path,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for sync
        )

        # Combine stdout and stderr for full output
        output = result.stdout
        if result.stderr:
            output = output + "\n" + result.stderr if output else result.stderr

        return SyncResult(
            package_name=package_name,
            success=result.returncode == 0,
            output=output.strip(),
            return_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        return SyncResult(
            package_name=package_name,
            success=False,
            output="Sync timed out after 300 seconds",
            return_code=-1,
        )

    except FileNotFoundError:
        return SyncResult(
            package_name=package_name,
            success=False,
            output="Error: 'uv' command not found. Please ensure UV is installed.",
            return_code=-1,
        )

    except OSError as e:
        return SyncResult(
            package_name=package_name,
            success=False,
            output=f"Error during sync: {e}",
            return_code=-1,
        )


def run_tests_in_package(
    package_path: Path,
    package_name: str,
    pytest_args: Optional[list[str]] = None,
    timeout: int = 600,
) -> TestResult:
    if pytest_args is None:
        pytest_args = []

    cmd = ["uv", "run", "pytest"] + pytest_args

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=package_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.time() - start_time

        # Combine stdout and stderr for full output
        output = result.stdout
        if result.stderr:
            output = output + "\n" + result.stderr if output else result.stderr

        return TestResult(
            package_name=package_name,
            passed=result.returncode == 0,
            duration=duration,
            output=output.strip(),
            return_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return TestResult(
            package_name=package_name,
            passed=False,
            duration=duration,
            output=f"Test execution timed out after {timeout} seconds",
            return_code=-1,
        )

    except FileNotFoundError:
        duration = time.time() - start_time
        return TestResult(
            package_name=package_name,
            passed=False,
            duration=duration,
            output="Error: 'uv' command not found. Please ensure UV is installed.",
            return_code=-1,
        )

    except OSError as e:
        duration = time.time() - start_time
        return TestResult(
            package_name=package_name,
            passed=False,
            duration=duration,
            output=f"Error running tests: {e}",
            return_code=-1,
        )


def run_tests_isolated(
    package_path: Path,
    package_name: str,
    test_dependencies: list[str],
    pytest_args: Optional[list[str]] = None,
    timeout: int = 600,
) -> TestResult:
    if pytest_args is None:
        pytest_args = []

    # Build command: uv run --isolated --with <deps> --with ./pkg pytest [args]
    cmd = ["uv", "run", "--isolated"]

    # Add test dependencies (e.g., pytest, pytest-cov)
    for dep in test_dependencies:
        cmd.extend(["--with", dep])

    # Add the package itself (installs package AND its dependencies from pyproject.toml)
    cmd.extend(["--with", str(package_path)])

    # Add pytest command and args
    cmd.append("pytest")
    cmd.extend(pytest_args)

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=package_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.time() - start_time

        # Combine stdout and stderr for full output
        output = result.stdout
        if result.stderr:
            output = output + "\n" + result.stderr if output else result.stderr

        return TestResult(
            package_name=package_name,
            passed=result.returncode == 0
            or result.returncode == 5,  # If no test are found it's ok
            duration=duration,
            output=output.strip(),
            return_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return TestResult(
            package_name=package_name,
            passed=False,
            duration=duration,
            output=f"Test execution timed out after {timeout} seconds",
            return_code=-1,
        )

    except FileNotFoundError:
        duration = time.time() - start_time
        return TestResult(
            package_name=package_name,
            passed=False,
            duration=duration,
            output="Error: 'uv' command not found. Please ensure UV is installed.",
            return_code=-1,
        )

    except OSError as e:
        duration = time.time() - start_time
        return TestResult(
            package_name=package_name,
            passed=False,
            duration=duration,
            output=f"Error running tests: {e}",
            return_code=-1,
        )
