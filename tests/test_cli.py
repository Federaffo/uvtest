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
                    test_dependencies=[],
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
                    test_dependencies=[],
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
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful test runs (isolated mode)
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.5
            mock_test_result.output = "All tests passed"
            mock_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run"])

            # Should exit with code 0 (all tests passed)
            assert result.exit_code == 0

    def test_run_exits_1_when_any_test_fails(self):
        """Verify run exits with code 1 when any test fails."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock test runs: first passes, second fails (isolated mode)
            mock_test_result_pass = Mock()
            mock_test_result_pass.passed = True
            mock_test_result_pass.duration = 1.0
            mock_test_result_pass.output = "Tests passed"

            mock_test_result_fail = Mock()
            mock_test_result_fail.passed = False
            mock_test_result_fail.duration = 2.0
            mock_test_result_fail.output = "Tests failed"

            mock_isolated.side_effect = [mock_test_result_pass, mock_test_result_fail]

            result = runner.invoke(main, ["run"])

            # Should exit with code 1 (at least one test failed)
            assert result.exit_code == 1

    def test_run_exits_1_when_sync_fails(self):
        """Verify run exits with code 1 when sync fails for a package (in sync mode)."""
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
                    test_dependencies=[],
                ),
            ]

            # Mock failed sync
            mock_sync_result = Mock()
            mock_sync_result.success = False
            mock_sync_result.output = "Sync failed: dependency resolution error"
            mock_sync.return_value = mock_sync_result

            result = runner.invoke(main, ["run", "--sync"])

            # Should exit with code 1 (sync failed)
            assert result.exit_code == 1
            assert "Failed to sync" in result.output

    def test_run_exits_1_when_all_tests_fail(self):
        """Verify run exits with code 1 when all tests fail."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock failed test run (isolated mode)
            mock_test_result = Mock()
            mock_test_result.passed = False
            mock_test_result.duration = 1.0
            mock_test_result.output = "All tests failed"
            mock_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run"])

            # Should exit with code 1
            assert result.exit_code == 1


class TestFailFastOption:
    """Test --fail-fast flag behavior."""

    def test_fail_fast_stops_after_first_failure(self):
        """Verify --fail-fast stops execution after first failing package."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock three packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="pkg-c",
                    path=Path("/fake/pkg-c"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-c/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock test runs: first fails, others should not be called (isolated mode)
            mock_test_result_fail = Mock()
            mock_test_result_fail.passed = False
            mock_test_result_fail.duration = 1.0
            mock_test_result_fail.output = "Tests failed"
            mock_isolated.return_value = mock_test_result_fail

            result = runner.invoke(main, ["run", "--fail-fast"])

            # Should exit with code 1
            assert result.exit_code == 1
            # Should show fail-fast message
            assert "Stopping execution due to --fail-fast" in result.output
            # Should only run tests once (for first package)
            assert mock_isolated.call_count == 1

    def test_without_fail_fast_continues_all_packages(self):
        """Verify without --fail-fast, execution continues through all packages."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock three packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="pkg-c",
                    path=Path("/fake/pkg-c"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-c/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock test runs: first fails, rest pass (isolated mode)
            mock_test_result_fail = Mock()
            mock_test_result_fail.passed = False
            mock_test_result_fail.duration = 1.0
            mock_test_result_fail.output = "Tests failed"

            mock_test_result_pass = Mock()
            mock_test_result_pass.passed = True
            mock_test_result_pass.duration = 1.0
            mock_test_result_pass.output = "Tests passed"

            mock_isolated.side_effect = [
                mock_test_result_fail,
                mock_test_result_pass,
                mock_test_result_pass,
            ]

            result = runner.invoke(main, ["run"])

            # Should exit with code 1 (first test failed)
            assert result.exit_code == 1
            # Should NOT show fail-fast message
            assert "Stopping execution due to --fail-fast" not in result.output
            # Should run tests for all three packages
            assert mock_isolated.call_count == 3

    def test_fail_fast_with_sync_failure(self):
        """Verify --fail-fast stops when sync fails."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.sync_package") as mock_sync,
            patch("uvtest.cli.run_tests_in_package") as mock_run,
        ):
            # Mock two packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock failed sync (first package fails sync)
            mock_sync_result = Mock()
            mock_sync_result.success = False
            mock_sync_result.output = "Sync failed"
            mock_sync.return_value = mock_sync_result

            result = runner.invoke(main, ["run", "--fail-fast"])

            # Should exit with code 1
            assert result.exit_code == 1
            # Should show fail-fast message
            assert "Stopping execution due to --fail-fast" in result.output
            # Should not run any tests (sync failed)
            assert mock_run.call_count == 0


class TestSyncModeFlag:
    """Test --sync flag behavior for switching between isolated and sync modes."""

    def test_default_uses_isolated_mode(self):
        """Verify default behavior (no --sync) uses isolated mode."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
            patch("uvtest.cli.sync_package") as mock_sync,
            patch("uvtest.cli.run_tests_in_package") as mock_run,
        ):
            # Mock packages with tests and test dependencies
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=["pytest>=7.0", "pytest-cov>=4.0"],
                ),
            ]

            # Mock successful isolated test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.5
            mock_test_result.output = "All tests passed"
            mock_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run"])

            # Should exit with code 0
            assert result.exit_code == 0
            # Should use isolated mode (run_tests_isolated called)
            assert mock_isolated.call_count == 1
            # Should NOT use sync mode
            assert mock_sync.call_count == 0
            assert mock_run.call_count == 0
            # Verify isolated runner was called with correct args
            mock_isolated.assert_called_once_with(
                Path("/fake/pkg-a"),
                "pkg-a",
                ["pytest>=7.0", "pytest-cov>=4.0"],
                pytest_args=None,
            )

    def test_sync_flag_uses_sync_mode(self):
        """Verify --sync flag uses sync mode (uv sync + uv run pytest)."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
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
                    test_dependencies=["pytest>=7.0"],
                ),
            ]

            # Mock successful sync
            mock_sync_result = Mock()
            mock_sync_result.success = True
            mock_sync_result.output = ""
            mock_sync.return_value = mock_sync_result

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_run.return_value = mock_test_result

            result = runner.invoke(main, ["run", "--sync"])

            # Should exit with code 0
            assert result.exit_code == 0
            # Should use sync mode
            assert mock_sync.call_count == 1
            assert mock_run.call_count == 1
            # Should NOT use isolated mode
            assert mock_isolated.call_count == 0

    def test_isolated_mode_with_empty_test_dependencies(self):
        """Verify isolated mode works with packages that have no test dependencies."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock package with no test dependencies
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful isolated test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run"])

            # Should exit with code 0
            assert result.exit_code == 0
            # Verify isolated runner was called with empty test_dependencies
            mock_isolated.assert_called_once_with(
                Path("/fake/pkg-a"),
                "pkg-a",
                [],
                pytest_args=None,
            )

    def test_sync_mode_with_multiple_packages(self):
        """Verify --sync mode works correctly with multiple packages."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.sync_package") as mock_sync,
            patch("uvtest.cli.run_tests_in_package") as mock_run,
        ):
            # Mock two packages with tests
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=["pytest"],
                ),
                Package(
                    name="pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                    test_dependencies=["pytest", "pytest-cov"],
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
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_run.return_value = mock_test_result

            result = runner.invoke(main, ["run", "--sync"])

            # Should exit with code 0
            assert result.exit_code == 0
            # Should sync and run tests for both packages
            assert mock_sync.call_count == 2
            assert mock_run.call_count == 2


class TestPackageFilter:
    """Test --package/-p flag for filtering packages."""

    def test_exact_name_match_works(self):
        """Verify exact package name match works."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock three packages
            mock_find.return_value = [
                Package(
                    name="mypackage",
                    path=Path("/fake/mypackage"),
                    has_tests=True,
                    pyproject_path=Path("/fake/mypackage/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="otherpackage",
                    path=Path("/fake/otherpackage"),
                    has_tests=True,
                    pyproject_path=Path("/fake/otherpackage/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="thirdpackage",
                    path=Path("/fake/thirdpackage"),
                    has_tests=True,
                    pyproject_path=Path("/fake/thirdpackage/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run", "--package", "mypackage"])

            # Should exit with code 0
            assert result.exit_code == 0
            # Should only run tests once (for mypackage)
            assert mock_isolated.call_count == 1
            # Verify it was called with the right package
            mock_isolated.assert_called_once_with(
                Path("/fake/mypackage"),
                "mypackage",
                [],
                pytest_args=None,
            )

    def test_glob_pattern_match_works(self):
        """Verify glob pattern matching works (e.g., 'core-*')."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock packages: two match 'core-*' pattern, one doesn't
            mock_find.return_value = [
                Package(
                    name="core-api",
                    path=Path("/fake/core-api"),
                    has_tests=True,
                    pyproject_path=Path("/fake/core-api/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="core-utils",
                    path=Path("/fake/core-utils"),
                    has_tests=True,
                    pyproject_path=Path("/fake/core-utils/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="service-worker",
                    path=Path("/fake/service-worker"),
                    has_tests=True,
                    pyproject_path=Path("/fake/service-worker/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run", "--package", "core-*"])

            # Should exit with code 0
            assert result.exit_code == 0
            # Should run tests twice (for core-api and core-utils)
            assert mock_isolated.call_count == 2

    def test_multiple_filters_work(self):
        """Verify multiple --package filters work (e.g., --package foo --package bar)."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock four packages
            mock_find.return_value = [
                Package(
                    name="foo",
                    path=Path("/fake/foo"),
                    has_tests=True,
                    pyproject_path=Path("/fake/foo/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="bar",
                    path=Path("/fake/bar"),
                    has_tests=True,
                    pyproject_path=Path("/fake/bar/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="baz",
                    path=Path("/fake/baz"),
                    has_tests=True,
                    pyproject_path=Path("/fake/baz/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="qux",
                    path=Path("/fake/qux"),
                    has_tests=True,
                    pyproject_path=Path("/fake/qux/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_isolated.return_value = mock_test_result

            result = runner.invoke(
                main, ["run", "--package", "foo", "--package", "bar"]
            )

            # Should exit with code 0
            assert result.exit_code == 0
            # Should run tests twice (for foo and bar only)
            assert mock_isolated.call_count == 2

    def test_short_flag_works(self):
        """Verify -p short flag works."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock two packages
            mock_find.return_value = [
                Package(
                    name="testpkg",
                    path=Path("/fake/testpkg"),
                    has_tests=True,
                    pyproject_path=Path("/fake/testpkg/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="otherpkg",
                    path=Path("/fake/otherpkg"),
                    has_tests=True,
                    pyproject_path=Path("/fake/otherpkg/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run", "-p", "testpkg"])

            # Should exit with code 0
            assert result.exit_code == 0
            # Should only run tests once (for testpkg)
            assert mock_isolated.call_count == 1

    def test_error_when_no_packages_match_filter(self):
        """Verify error is shown when no packages match the filter."""
        runner = CliRunner()

        with patch("uvtest.cli.find_packages") as mock_find:
            # Mock packages that don't match the filter
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            result = runner.invoke(main, ["run", "--package", "nonexistent"])

            # Should exit with code 1
            assert result.exit_code == 1
            # Should show error message with the filter name
            assert "No packages match the filter" in result.output
            assert "nonexistent" in result.output

    def test_filter_preserves_fail_fast_behavior(self):
        """Verify --package filter works with --fail-fast."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_isolated,
        ):
            # Mock three packages matching 'pkg-*' pattern
            mock_find.return_value = [
                Package(
                    name="pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="other-pkg",
                    path=Path("/fake/other-pkg"),
                    has_tests=True,
                    pyproject_path=Path("/fake/other-pkg/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock failed test for first package
            mock_test_result = Mock()
            mock_test_result.passed = False
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests failed"
            mock_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run", "--package", "pkg-*", "--fail-fast"])

            # Should exit with code 1
            assert result.exit_code == 1
            # Should stop after first failure
            assert mock_isolated.call_count == 1
            # Should show fail-fast message
            assert "Stopping execution due to --fail-fast" in result.output

    def test_filter_works_with_sync_mode(self):
        """Verify --package filter works with --sync mode."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.sync_package") as mock_sync,
            patch("uvtest.cli.run_tests_in_package") as mock_run,
        ):
            # Mock three packages
            mock_find.return_value = [
                Package(
                    name="selected",
                    path=Path("/fake/selected"),
                    has_tests=True,
                    pyproject_path=Path("/fake/selected/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="notselected",
                    path=Path("/fake/notselected"),
                    has_tests=True,
                    pyproject_path=Path("/fake/notselected/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful sync
            mock_sync_result = Mock()
            mock_sync_result.success = True
            mock_sync_result.output = ""
            mock_sync.return_value = mock_sync_result

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_run.return_value = mock_test_result

            result = runner.invoke(main, ["run", "--sync", "--package", "selected"])

            # Should exit with code 0
            assert result.exit_code == 0
            # Should sync and run only the selected package
            assert mock_sync.call_count == 1
            assert mock_run.call_count == 1


class TestPytestPassthrough:
    """Test passing additional arguments to pytest via -- separator."""

    def test_pytest_args_passed_to_isolated_runner(self):
        """Verify pytest args are passed to run_tests_isolated in isolated mode."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_run_isolated,
        ):
            # Mock one package
            mock_find.return_value = [
                Package(
                    name="test-pkg",
                    path=Path("/fake/pkg"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg/pyproject.toml"),
                    test_dependencies=["pytest>=7.0"],
                ),
            ]

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_run_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run", "--", "-k", "test_foo"])

            # Should exit with code 0
            assert result.exit_code == 0

            # Verify run_tests_isolated was called with pytest args
            assert mock_run_isolated.call_count == 1
            call_args = mock_run_isolated.call_args
            # Check that pytest_args contains ["-k", "test_foo"]
            assert call_args.kwargs["pytest_args"] == ["-k", "test_foo"]

    def test_pytest_args_passed_to_sync_runner(self):
        """Verify pytest args are passed to run_tests_in_package in sync mode."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.sync_package") as mock_sync,
            patch("uvtest.cli.run_tests_in_package") as mock_run,
        ):
            # Mock one package
            mock_find.return_value = [
                Package(
                    name="test-pkg",
                    path=Path("/fake/pkg"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful sync
            mock_sync_result = Mock()
            mock_sync_result.success = True
            mock_sync_result.output = ""
            mock_sync.return_value = mock_sync_result

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_run.return_value = mock_test_result

            result = runner.invoke(main, ["run", "--sync", "--", "-v", "-s"])

            # Should exit with code 0
            assert result.exit_code == 0

            # Verify run_tests_in_package was called with pytest args
            assert mock_run.call_count == 1
            call_args = mock_run.call_args
            # Check that pytest_args contains ["-v", "-s"]
            assert call_args.kwargs["pytest_args"] == ["-v", "-s"]

    def test_multiple_pytest_args_passed(self):
        """Verify multiple pytest args are passed correctly."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_run_isolated,
        ):
            # Mock one package
            mock_find.return_value = [
                Package(
                    name="test-pkg",
                    path=Path("/fake/pkg"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_run_isolated.return_value = mock_test_result

            result = runner.invoke(
                main, ["run", "--", "-x", "--tb=short", "-k", "test_foo"]
            )

            # Should exit with code 0
            assert result.exit_code == 0

            # Verify pytest args contain all arguments
            call_args = mock_run_isolated.call_args
            assert call_args.kwargs["pytest_args"] == [
                "-x",
                "--tb=short",
                "-k",
                "test_foo",
            ]

    def test_no_pytest_args_passes_none(self):
        """Verify that when no pytest args are provided, None is passed."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_run_isolated,
        ):
            # Mock one package
            mock_find.return_value = [
                Package(
                    name="test-pkg",
                    path=Path("/fake/pkg"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_run_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run"])

            # Should exit with code 0
            assert result.exit_code == 0

            # Verify pytest_args is None when no args provided
            call_args = mock_run_isolated.call_args
            assert call_args.kwargs["pytest_args"] is None

    def test_pytest_args_work_with_package_filter(self):
        """Verify pytest args work correctly with --package filter."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_run_isolated,
        ):
            # Mock two packages
            mock_find.return_value = [
                Package(
                    name="test-pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="test-pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock successful test run
            mock_test_result = Mock()
            mock_test_result.passed = True
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests passed"
            mock_run_isolated.return_value = mock_test_result

            result = runner.invoke(
                main, ["run", "--package", "test-pkg-a", "--", "-k", "test_integration"]
            )

            # Should exit with code 0
            assert result.exit_code == 0

            # Verify run_tests_isolated called only once (filtered package)
            assert mock_run_isolated.call_count == 1

            # Verify pytest args were passed
            call_args = mock_run_isolated.call_args
            assert call_args.kwargs["pytest_args"] == ["-k", "test_integration"]

    def test_pytest_args_work_with_fail_fast(self):
        """Verify pytest args work correctly with --fail-fast."""
        runner = CliRunner()

        with (
            patch("uvtest.cli.find_packages") as mock_find,
            patch("uvtest.cli.run_tests_isolated") as mock_run_isolated,
        ):
            # Mock two packages
            mock_find.return_value = [
                Package(
                    name="test-pkg-a",
                    path=Path("/fake/pkg-a"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-a/pyproject.toml"),
                    test_dependencies=[],
                ),
                Package(
                    name="test-pkg-b",
                    path=Path("/fake/pkg-b"),
                    has_tests=True,
                    pyproject_path=Path("/fake/pkg-b/pyproject.toml"),
                    test_dependencies=[],
                ),
            ]

            # Mock first test failing
            mock_test_result = Mock()
            mock_test_result.passed = False
            mock_test_result.duration = 1.0
            mock_test_result.output = "Tests failed"
            mock_run_isolated.return_value = mock_test_result

            result = runner.invoke(main, ["run", "--fail-fast", "--", "-v"])

            # Should exit with code 1 (test failed)
            assert result.exit_code == 1

            # Verify run_tests_isolated called only once (fail-fast)
            assert mock_run_isolated.call_count == 1

            # Verify pytest args were passed
            call_args = mock_run_isolated.call_args
            assert call_args.kwargs["pytest_args"] == ["-v"]

            # Verify fail-fast message appeared
            assert "Stopping execution due to --fail-fast" in result.output
