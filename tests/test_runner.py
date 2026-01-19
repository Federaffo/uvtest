"""Tests for test runner module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uvtest.runner import (
    SyncResult,
    TestResult,
    run_tests_in_package,
    run_tests_isolated,
    sync_package,
)


class TestTestResult:
    """Tests for TestResult dataclass."""

    def test_testresult_fields(self):
        result = TestResult(
            package_name="my-package",
            passed=True,
            duration=1.5,
            output="All tests passed",
            return_code=0,
        )
        assert result.package_name == "my-package"
        assert result.passed is True
        assert result.duration == 1.5
        assert result.output == "All tests passed"
        assert result.return_code == 0

    def test_testresult_failure(self):
        result = TestResult(
            package_name="failing-pkg",
            passed=False,
            duration=2.0,
            output="FAILED test_something",
            return_code=1,
        )
        assert result.passed is False
        assert result.return_code == 1


class TestRunTestsInPackage:
    """Tests for run_tests_in_package function."""

    def test_successful_test_run(self, tmp_path: Path):
        """Test successful pytest execution."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="===== 5 passed in 0.5s =====",
                stderr="",
            )

            result = run_tests_in_package(tmp_path, "test-pkg")

            assert result.passed is True
            assert result.package_name == "test-pkg"
            assert result.return_code == 0
            assert "5 passed" in result.output
            assert result.duration >= 0

            # Verify correct command was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args.kwargs["cwd"] == tmp_path
            assert call_args.args[0] == ["uv", "run", "pytest"]

    def test_failed_test_run(self, tmp_path: Path):
        """Test failed pytest execution."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="FAILED tests/test_foo.py::test_bar",
                stderr="",
            )

            result = run_tests_in_package(tmp_path, "failing-pkg")

            assert result.passed is False
            assert result.return_code == 1
            assert "FAILED" in result.output

    def test_passes_additional_pytest_args(self, tmp_path: Path):
        """Test that additional pytest args are passed through."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1 passed",
                stderr="",
            )

            run_tests_in_package(
                tmp_path, "test-pkg", pytest_args=["-v", "-k", "test_foo"]
            )

            call_args = mock_run.call_args
            assert call_args.args[0] == ["uv", "run", "pytest", "-v", "-k", "test_foo"]

    def test_handles_timeout(self, tmp_path: Path):
        """Test that timeout is handled gracefully."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=5)

            result = run_tests_in_package(tmp_path, "slow-pkg", timeout=5)

            assert result.passed is False
            assert result.return_code == -1
            assert "timed out" in result.output.lower()

    def test_handles_uv_not_found(self, tmp_path: Path):
        """Test handling when uv command is not found."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("uv not found")

            result = run_tests_in_package(tmp_path, "test-pkg")

            assert result.passed is False
            assert result.return_code == -1
            assert "uv" in result.output.lower()

    def test_handles_os_error(self, tmp_path: Path):
        """Test handling of other OS errors."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Permission denied")

            result = run_tests_in_package(tmp_path, "test-pkg")

            assert result.passed is False
            assert result.return_code == -1
            assert "error" in result.output.lower()

    def test_combines_stdout_and_stderr(self, tmp_path: Path):
        """Test that both stdout and stderr are captured."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test output",
                stderr="some warnings",
            )

            result = run_tests_in_package(tmp_path, "test-pkg")

            assert "test output" in result.output
            assert "some warnings" in result.output

    def test_handles_empty_output(self, tmp_path: Path):
        """Test handling of empty stdout/stderr."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="",
            )

            result = run_tests_in_package(tmp_path, "test-pkg")

            assert result.passed is True
            assert result.output == ""

    def test_default_timeout(self, tmp_path: Path):
        """Test that default timeout is 600 seconds (10 minutes)."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="passed",
                stderr="",
            )

            run_tests_in_package(tmp_path, "test-pkg")

            call_args = mock_run.call_args
            assert call_args.kwargs["timeout"] == 600

    def test_custom_timeout(self, tmp_path: Path):
        """Test that custom timeout is used."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="passed",
                stderr="",
            )

            run_tests_in_package(tmp_path, "test-pkg", timeout=120)

            call_args = mock_run.call_args
            assert call_args.kwargs["timeout"] == 120

    def test_strips_output(self, tmp_path: Path):
        """Test that output is stripped of leading/trailing whitespace."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="  test output  \n\n",
                stderr="",
            )

            result = run_tests_in_package(tmp_path, "test-pkg")

            assert result.output == "test output"

    def test_duration_is_measured(self, tmp_path: Path):
        """Test that duration is measured correctly."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="passed",
                stderr="",
            )

            result = run_tests_in_package(tmp_path, "test-pkg")

            # Duration should be a positive number
            assert result.duration >= 0
            # Duration should be reasonable (less than a second for mocked run)
            assert result.duration < 1.0

    def test_pytest_args_none_default(self, tmp_path: Path):
        """Test that pytest_args defaults to empty list."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="passed",
                stderr="",
            )

            run_tests_in_package(tmp_path, "test-pkg")

            call_args = mock_run.call_args
            # Should be just ["uv", "run", "pytest"] with no extra args
            assert call_args.args[0] == ["uv", "run", "pytest"]

    def test_return_code_passed_through(self, tmp_path: Path):
        """Test various pytest return codes are passed through."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            # Test exit code 2 (test collection error)
            mock_run.return_value = MagicMock(
                returncode=2,
                stdout="collection error",
                stderr="",
            )

            result = run_tests_in_package(tmp_path, "test-pkg")

            assert result.return_code == 2
            assert result.passed is False

    def test_only_stderr_output(self, tmp_path: Path):
        """Test handling when only stderr has output."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="error message",
            )

            result = run_tests_in_package(tmp_path, "test-pkg")

            assert result.output == "error message"


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_syncresult_fields(self):
        result = SyncResult(
            package_name="my-package",
            success=True,
            output="Synced successfully",
            return_code=0,
        )
        assert result.package_name == "my-package"
        assert result.success is True
        assert result.output == "Synced successfully"
        assert result.return_code == 0

    def test_syncresult_failure(self):
        result = SyncResult(
            package_name="failing-pkg",
            success=False,
            output="Sync failed",
            return_code=1,
        )
        assert result.success is False
        assert result.return_code == 1


class TestSyncPackage:
    """Tests for sync_package function."""

    def test_successful_sync(self, tmp_path: Path):
        """Test successful uv sync execution."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Resolved 5 packages",
                stderr="",
            )

            result = sync_package(tmp_path, "test-pkg")

            assert result.success is True
            assert result.package_name == "test-pkg"
            assert result.return_code == 0
            assert "Resolved" in result.output

            # Verify correct command was called with --quiet
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args.kwargs["cwd"] == tmp_path
            assert call_args.args[0] == ["uv", "sync", "--quiet"]

    def test_sync_with_verbose(self, tmp_path: Path):
        """Test sync in verbose mode (no --quiet flag)."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Resolved 5 packages in 1.2s",
                stderr="",
            )

            result = sync_package(tmp_path, "test-pkg", verbose=True)

            assert result.success is True

            # Verify --quiet is NOT in command
            call_args = mock_run.call_args
            assert call_args.args[0] == ["uv", "sync"]

    def test_failed_sync(self, tmp_path: Path):
        """Test failed uv sync execution."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="error: failed to resolve dependencies",
            )

            result = sync_package(tmp_path, "failing-pkg")

            assert result.success is False
            assert result.return_code == 1
            assert "error" in result.output.lower()

    def test_sync_handles_timeout(self, tmp_path: Path):
        """Test that sync timeout is handled gracefully."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="uv sync", timeout=300)

            result = sync_package(tmp_path, "slow-pkg")

            assert result.success is False
            assert result.return_code == -1
            assert "timed out" in result.output.lower()

    def test_sync_handles_uv_not_found(self, tmp_path: Path):
        """Test handling when uv command is not found."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("uv not found")

            result = sync_package(tmp_path, "test-pkg")

            assert result.success is False
            assert result.return_code == -1
            assert "uv" in result.output.lower()

    def test_sync_handles_os_error(self, tmp_path: Path):
        """Test handling of other OS errors during sync."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Permission denied")

            result = sync_package(tmp_path, "test-pkg")

            assert result.success is False
            assert result.return_code == -1
            assert "error" in result.output.lower()

    def test_sync_combines_stdout_and_stderr(self, tmp_path: Path):
        """Test that both stdout and stderr are captured."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="sync output",
                stderr="some warnings",
            )

            result = sync_package(tmp_path, "test-pkg")

            assert "sync output" in result.output
            assert "some warnings" in result.output

    def test_sync_timeout_is_300_seconds(self, tmp_path: Path):
        """Test that sync timeout is 5 minutes (300 seconds)."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="synced",
                stderr="",
            )

            sync_package(tmp_path, "test-pkg")

            call_args = mock_run.call_args
            assert call_args.kwargs["timeout"] == 300

    def test_sync_strips_output(self, tmp_path: Path):
        """Test that output is stripped of whitespace."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="  synced  \n\n",
                stderr="",
            )

            result = sync_package(tmp_path, "test-pkg")

            assert result.output == "synced"


class TestRunTestsIsolated:
    """Tests for run_tests_isolated function."""

    def test_builds_correct_command_with_dependencies(self, tmp_path: Path):
        """Test that command is built correctly with test dependencies."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="===== 5 passed in 0.5s =====",
                stderr="",
            )

            test_deps = ["pytest>=7.0", "pytest-cov>=4.0"]
            result = run_tests_isolated(tmp_path, "test-pkg", test_deps)

            assert result.passed is True
            assert result.package_name == "test-pkg"
            assert result.return_code == 0

            # Verify correct command was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args.kwargs["cwd"] == tmp_path

            cmd = call_args.args[0]
            assert cmd[0:3] == ["uv", "run", "--isolated"]
            assert "--with" in cmd
            assert "pytest>=7.0" in cmd
            assert "--with" in cmd
            assert "pytest-cov>=4.0" in cmd
            assert "--with" in cmd
            assert str(tmp_path) in cmd
            assert "pytest" in cmd

    def test_empty_test_dependencies(self, tmp_path: Path):
        """Test isolated runner with no test dependencies."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="passed",
                stderr="",
            )

            result = run_tests_isolated(tmp_path, "test-pkg", [])

            assert result.passed is True

            call_args = mock_run.call_args
            cmd = call_args.args[0]
            # Should have: uv run --isolated --with ./path pytest
            assert cmd[0:3] == ["uv", "run", "--isolated"]
            assert "--with" in cmd
            assert str(tmp_path) in cmd
            assert cmd[-1] == "pytest"

    def test_passes_pytest_args(self, tmp_path: Path):
        """Test that pytest args are passed through."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1 passed",
                stderr="",
            )

            test_deps = ["pytest"]
            result = run_tests_isolated(
                tmp_path, "test-pkg", test_deps, pytest_args=["-v", "-k", "test_foo"]
            )

            assert result.passed is True

            call_args = mock_run.call_args
            cmd = call_args.args[0]
            # pytest args should be at the end after "pytest"
            assert cmd[-4:] == ["pytest", "-v", "-k", "test_foo"]

    def test_failed_test_run(self, tmp_path: Path):
        """Test failed pytest execution in isolated mode."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="FAILED tests/test_foo.py::test_bar",
                stderr="",
            )

            result = run_tests_isolated(tmp_path, "failing-pkg", ["pytest"])

            assert result.passed is False
            assert result.return_code == 1
            assert "FAILED" in result.output

    def test_handles_timeout(self, tmp_path: Path):
        """Test that timeout is handled gracefully."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=5)

            result = run_tests_isolated(tmp_path, "slow-pkg", ["pytest"], timeout=5)

            assert result.passed is False
            assert result.return_code == -1
            assert "timed out" in result.output.lower()

    def test_handles_uv_not_found(self, tmp_path: Path):
        """Test handling when uv command is not found."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("uv not found")

            result = run_tests_isolated(tmp_path, "test-pkg", ["pytest"])

            assert result.passed is False
            assert result.return_code == -1
            assert "uv" in result.output.lower()

    def test_handles_os_error(self, tmp_path: Path):
        """Test handling of other OS errors."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Permission denied")

            result = run_tests_isolated(tmp_path, "test-pkg", ["pytest"])

            assert result.passed is False
            assert result.return_code == -1
            assert "error" in result.output.lower()

    def test_combines_stdout_and_stderr(self, tmp_path: Path):
        """Test that both stdout and stderr are captured."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test output",
                stderr="some warnings",
            )

            result = run_tests_isolated(tmp_path, "test-pkg", ["pytest"])

            assert "test output" in result.output
            assert "some warnings" in result.output

    def test_default_timeout(self, tmp_path: Path):
        """Test that default timeout is 600 seconds (10 minutes)."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="passed",
                stderr="",
            )

            run_tests_isolated(tmp_path, "test-pkg", ["pytest"])

            call_args = mock_run.call_args
            assert call_args.kwargs["timeout"] == 600

    def test_custom_timeout(self, tmp_path: Path):
        """Test that custom timeout is used."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="passed",
                stderr="",
            )

            run_tests_isolated(tmp_path, "test-pkg", ["pytest"], timeout=120)

            call_args = mock_run.call_args
            assert call_args.kwargs["timeout"] == 120

    def test_duration_is_measured(self, tmp_path: Path):
        """Test that duration is measured correctly."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="passed",
                stderr="",
            )

            result = run_tests_isolated(tmp_path, "test-pkg", ["pytest"])

            # Duration should be a positive number
            assert result.duration >= 0
            # Duration should be reasonable (less than a second for mocked run)
            assert result.duration < 1.0

    def test_strips_output(self, tmp_path: Path):
        """Test that output is stripped of leading/trailing whitespace."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="  test output  \n\n",
                stderr="",
            )

            result = run_tests_isolated(tmp_path, "test-pkg", ["pytest"])

            assert result.output == "test output"

    def test_multiple_test_dependencies(self, tmp_path: Path):
        """Test command construction with multiple test dependencies."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="passed",
                stderr="",
            )

            test_deps = ["pytest>=7.0", "pytest-cov>=4.0", "pytest-mock>=3.0"]
            run_tests_isolated(tmp_path, "test-pkg", test_deps)

            call_args = mock_run.call_args
            cmd = call_args.args[0]

            # Verify all dependencies are in the command with --with flags
            assert cmd.count("--with") == 4  # 3 deps + package itself
            assert "pytest>=7.0" in cmd
            assert "pytest-cov>=4.0" in cmd
            assert "pytest-mock>=3.0" in cmd
            assert str(tmp_path) in cmd

    def test_package_path_is_included(self, tmp_path: Path):
        """Test that package path is included with --with flag."""
        with patch("uvtest.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="passed",
                stderr="",
            )

            package_path = tmp_path / "my-package"
            run_tests_isolated(package_path, "my-package", ["pytest"])

            call_args = mock_run.call_args
            cmd = call_args.args[0]

            # Package path should be in command
            assert str(package_path) in cmd
            # Should be preceded by --with
            pkg_idx = cmd.index(str(package_path))
            assert cmd[pkg_idx - 1] == "--with"
