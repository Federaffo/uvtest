"""Tests for test runner module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uvtest.runner import TestResult, run_tests_in_package


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
