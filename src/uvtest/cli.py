"""CLI entry point for uvtest."""

import sys
from pathlib import Path

import click

from uvtest import __version__
from uvtest.discovery import find_packages


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
        return

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


if __name__ == "__main__":
    main()
