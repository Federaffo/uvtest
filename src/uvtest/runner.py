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


def run_tests_in_package(
    package_path: Path,
    package_name: str,
    pytest_args: Optional[list[str]] = None,
    timeout: int = 600,
) -> TestResult:
    """Run pytest in a package directory using 'uv run pytest'.

    Args:
        package_path: Path to the package directory.
        package_name: Name of the package (for reporting).
        pytest_args: Additional arguments to pass to pytest.
        timeout: Maximum time in seconds to wait for tests (default: 10 minutes).

    Returns:
        TestResult with package_name, passed status, duration, output, and return_code.
    """
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
