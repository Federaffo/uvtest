"""Unit tests for CLI commands and exit codes."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from uvtest.cli import main
from uvtest.discovery import Package


class TestScanCommandExitCodes:
    """Test exit codes for the scan command."""

    def test_scan_exits_1_when_no_packages_found(self):
        """Verify scan exits with code 1 when no packages are found."""
        runner = CliRunner()

        with patch("uvtest.cli.find_packages") as mock_find:
            # Mock no packages found
            mock_find.return_value = []

            result = runner.invoke(main, ["scan"])

            # Should exit with code 1
            assert result.exit_code == 1
            assert "No packages with tests found." in result.output

    def test_scan_exits_0_when_packages_found(self):
        """Verify scan exits with code 0 when packages are found."""
        runner = CliRunner()

        with patch("uvtest.cli.find_packages") as mock_find:
            # Mock packages with tests
            mock_find.return_value = [
                Package(
                    name="test-pkg",
                    path=Path("/fake/pkg"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg/pyproject.toml"),
                )
            ]

            result = runner.invoke(main, ["scan"])

            # Should exit with code 0
            assert result.exit_code == 0
            assert "test-pkg" in result.output

    def test_scan_exits_1_when_no_packages_have_tests(self):
        """Verify scan exits with code 1 when no packages have tests."""
        runner = CliRunner()

        with patch("uvtest.cli.find_packages") as mock_find:
            # Mock packages without tests
            mock_find.return_value = [
                Package(
                    name="no-tests-pkg",
                    path=Path("/fake/pkg"),
                    has_tests=False,
                    pyproject_path=Path("/fake/pkg/pyproject.toml"),
                )
            ]

            result = runner.invoke(main, ["scan"])

            # Should exit with code 1 (no packages with tests)
            assert result.exit_code == 1
            assert "No packages with tests found." in result.output


class TestRunCommandExitCodes:
    """Test exit codes for the run command."""

    def test_run_exits_1_when_no_packages_found(self):
        """Verify run exits with code 1 when no packages are found."""
        runner = CliRunner()

        with patch("uvtest.cli.find_packages") as mock_find:
            # Mock no packages found
            mock_find.return_value = []

            result = runner.invoke(main, ["run"])

            # Should exit with code 1
            assert result.exit_code == 1
            assert "No packages with tests found." in result.output

    def test_run_exits_0_when_all_tests_pass(self):
        """Verify run exits with code 0 when all tests pass."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.sync_package") as mock_sync,
            patch("uvtest.cli.run_tests_in_package") as mock_run,
        ):
            # Mock packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                ),
                Package(
                    name="pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                ),
            ]

            # Mock successful sync
            mock_sync_result = Mock()
            mock_sync_result.success = True
            mock_sync_result.output = ""
            mock_sync.return_value = mock_sync_result

            # Mock successful test runs
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.5
            mock_test_result.output = "All tests passed"
            mock_run.return_value = mock_test_result

            result = runner.invoke(main, ["run"])

            # Should exit with code 0 (all tests passed)
            assert result.exit_code == 0

    def test_run_exits_1_when_any_test_fails(self):
        """Verify run exits with code 1 when any test fails."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.sync_package") as mock_sync,
            patch("uvtest.cli.run_tests_in_package") as mock_run,
        ):
            # Mock packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                ),
                Package(
                    name="pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                ),
            ]

            # Mock successful sync
            mock_sync_result = Mock()
            mock_sync_result.success = True
            mock_sync_result.output = ""
            mock_sync.return_value = mock_sync_result

            # Mock test runs: first passes, second fails
            mock_test_result_pass = Mock()
            mock_test_result_pass.passed = True
            mock_test_result_pass.duration = 1.0
            mock_test_result_pass.output = "Tests passed"

            mock_test_result_fail = Mock()
            mock_test_result_fail.passed = False
            mock_test_result_fail.duration = 2.0
            mock_test_result_fail.output = "Tests failed"

            mock_run.side_effect = [mock_test_result_pass, mock_test_result_fail]

            result = runner.invoke(main, ["run"])

            # Should exit with code 1 (at least one test failed)
            assert result.exit_code == 1

    def test_run_exits_1_when_sync_fails(self):
        """Verify run exits with code 1 when sync fails for a package."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.sync_package") as mock_sync,
        ):
            # Mock packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                ),
            ]

            # Mock failed sync
            mock_sync_result = Mock()
            mock_sync_result.success = False
            mock_sync_result.output = "Sync failed: dependency resolution error"
            mock_sync.return_value = mock_sync_result

            result = runner.invoke(main, ["run"])

            # Should exit with code 1 (sync failed)
            assert result.exit_code == 1
            assert "Failed to sync" in result.output

    def test_run_exits_1_when_all_tests_fail(self):
        """Verify run exits with code 1 when all tests fail."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.sync_package") as mock_sync,
            patch("uvtest.cli.run_tests_in_package") as mock_run,
        ):
            # Mock packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                ),
            ]

            # Mock successful sync
            mock_sync_result = Mock()
            mock_sync_result.success = True
            mock_sync_result.output = ""
            mock_sync.return_value = mock_sync_result

            # Mock failed test run
            mock_test_result = Mock()
            mock_test_result.passed = False
            mock_test_result.duration = 1.0
            mock_test_result.output = "All tests failed"
            mock_run.return_value = mock_test_result

            result = runner.invoke(main, ["run"])

            # Should exit with code 1
            assert result.exit_code == 1
