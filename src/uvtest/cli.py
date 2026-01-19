"""CLI entry point for uvtest."""

import fnmatch
import sys
from pathlib import Path

import click

from uvtest import __version__
from uvtest.discovery import find_packages
from uvtest.runner import run_tests_in_package, run_tests_isolated, sync_package


@click.group()
@click.version_option(version=__version__, prog_name="uvtest")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity. Use -v for verbose, -vv for very verbose.",
)
@click.pass_context
def main(ctx: click.Context, verbose: int) -> None:
    """uvtest - Run pytest tests across all packages in a UV monorepo.

    A CLI tool to discover and run pytest tests across all packages in a UV
    monorepo. Supports scanning packages, running tests with verbose output,
    coverage reports, and package filtering.

    Use 'uvtest COMMAND --help' for more information on a specific command.
    """
    # Ensure ctx.obj exists and store verbose level for subcommands
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@main.command()
@click.pass_context
def scan(ctx: click.Context) -> None:
    """Scan and list all packages with tests in the monorepo.

    Discovers all packages (subdirectories with pyproject.toml) and lists
    those that have a tests/ or test/ directory. Packages without tests
    are silently skipped.
    """
    verbose = ctx.obj.get("verbose", 0)

    # Discover all packages from current directory
    packages = find_packages(Path.cwd())

    # Filter to only packages with tests
    packages_with_tests = [p for p in packages if p.has_tests]

    if not packages_with_tests:
        click.echo("No packages with tests found.")
        sys.exit(1)

    # Determine if we should use colors (TTY detection)
    use_color = sys.stdout.isatty()

    # Display each package with tests
    for pkg in packages_with_tests:
        # Get relative path from cwd
        try:
            rel_path = pkg.path.relative_to(Path.cwd())
            path_str = f"./{rel_path}"
        except ValueError:
            # If path is not relative to cwd, use absolute
            path_str = str(pkg.path)

        if use_color:
            # Use cyan for package name
            name_styled = click.style(pkg.name, fg="cyan", bold=True)
            click.echo(f"{name_styled}  {path_str}")
        else:
            click.echo(f"{pkg.name}  {path_str}")

    # Show total count
    count = len(packages_with_tests)
    count_msg = f"\n{count} package{'s' if count != 1 else ''} with tests found."
    if use_color:
        click.echo(click.style(count_msg, fg="green"))
    else:
        click.echo(count_msg)


@main.command()
@click.option(
    "--fail-fast",
    is_flag=True,
    default=False,
    help="Stop execution after the first package with failing tests.",
)
@click.option(
    "--sync",
    is_flag=True,
    default=False,
    help="Use sync mode (cached venv) instead of isolated mode (default). "
    "Isolated mode creates fresh ephemeral environments for hermetic CI runs. "
    "Sync mode runs 'uv sync' and reuses .venv for faster repeated local runs.",
)
@click.option(
    "--package",
    "-p",
    multiple=True,
    help="Filter packages by name. Supports glob patterns (e.g., 'core-*'). "
    "Can be specified multiple times to test multiple packages.",
)
@click.pass_context
def run(
    ctx: click.Context, fail_fast: bool, sync: bool, package: tuple[str, ...]
) -> None:
    """Run tests across all packages in the monorepo.

    By default, uses ISOLATED MODE for hermetic test execution (better for CI).
    Each package runs in a fresh ephemeral environment with no cache pollution.

    With --sync flag, uses SYNC MODE for faster local development. Runs 'uv sync'
    to install dependencies into cached .venv, then executes pytest.

    Use -v to see package names as they complete.
    Use -vv to see full pytest output for each package.
    Use --fail-fast to stop after the first failure.
    """
    verbose = ctx.obj.get("verbose", 0)
    use_color = sys.stdout.isatty()

    # Discover all packages with tests
    packages = find_packages(Path.cwd())
    packages_with_tests = [p for p in packages if p.has_tests]

    # Apply package filter if specified
    if package:
        filtered_packages = []
        for pkg in packages_with_tests:
            # Check if package name matches any of the filter patterns
            for pattern in package:
                if fnmatch.fnmatch(pkg.name, pattern):
                    filtered_packages.append(pkg)
                    break

        packages_with_tests = filtered_packages

        # Show error if filter matched nothing
        if not packages_with_tests:
            error_msg = f"No packages match the filter(s): {', '.join(package)}"
            if use_color:
                click.echo(click.style(error_msg, fg="red"))
            else:
                click.echo(error_msg)
            sys.exit(1)

    if not packages_with_tests:
        click.echo("No packages with tests found.")
        sys.exit(1)

    # Track results
    results = []

    # Run tests in each package
    for pkg in packages_with_tests:
        # Show which package is being tested (unless verbosity is 0)
        if verbose >= 1:
            pkg_name_display = (
                click.style(pkg.name, fg="cyan", bold=True) if use_color else pkg.name
            )
            click.echo(f"\nTesting {pkg_name_display}...")

        # SYNC MODE: Run uv sync first, then pytest
        if sync:
            # Run uv sync first
            sync_result = sync_package(pkg.path, pkg.name, verbose=verbose >= 2)

            if not sync_result.success:
                # Sync failed - show error and skip package
                error_msg = f"Failed to sync {pkg.name}: {sync_result.output}"
                if use_color:
                    click.echo(click.style(error_msg, fg="red"))
                else:
                    click.echo(error_msg)
                results.append((pkg.name, False, 0.0))

                # Check fail-fast: stop if sync failed
                if fail_fast:
                    fail_fast_msg = "\nStopping execution due to --fail-fast (first failure detected)."
                    if use_color:
                        click.echo(click.style(fail_fast_msg, fg="yellow", bold=True))
                    else:
                        click.echo(fail_fast_msg)
                    break

                continue

            # Show sync success in very verbose mode
            if verbose >= 2 and sync_result.output:
                click.echo(f"Sync output:\n{sync_result.output}")

            # Run tests using sync mode (uv run pytest)
            test_result = run_tests_in_package(pkg.path, pkg.name)
        else:
            # ISOLATED MODE (default): Use isolated runner with ephemeral environment
            test_result = run_tests_isolated(pkg.path, pkg.name, pkg.test_dependencies)

        results.append((pkg.name, test_result.passed, test_result.duration))

        # Show results based on verbosity
        if verbose >= 2:
            # Show full pytest output
            click.echo(test_result.output)

        if verbose >= 1:
            # Show pass/fail status
            if test_result.passed:
                status = click.style("✓ PASSED", fg="green") if use_color else "PASSED"
            else:
                status = click.style("✗ FAILED", fg="red") if use_color else "FAILED"
            click.echo(f"{pkg.name}: {status}")

        # Check fail-fast: stop if this test failed
        if fail_fast and not test_result.passed:
            fail_fast_msg = (
                "\nStopping execution due to --fail-fast (first failure detected)."
            )
            if use_color:
                click.echo(click.style(fail_fast_msg, fg="yellow", bold=True))
            else:
                click.echo(fail_fast_msg)
            break

    # Minimal output mode (verbose == 0): just show package names with status
    if verbose == 0:
        click.echo("\nTest Results:")
        for pkg_name, passed, duration in results:
            if use_color:
                if passed:
                    status = click.style("✓", fg="green")
                else:
                    status = click.style("✗", fg="red")
            else:
                status = "✓" if passed else "✗"
            click.echo(f"{status} {pkg_name}")

    # Exit with appropriate code for CI/CD integration
    # Exit 1 if any test failed, exit 0 if all passed
    any_failed = any(not passed for _, passed, _ in results)
    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
