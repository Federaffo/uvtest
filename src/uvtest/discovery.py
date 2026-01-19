"""Package discovery for UV monorepos."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Use tomllib for Python 3.11+, fallback to tomli for 3.10
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


# Directories to skip during discovery
SKIP_DIRS = frozenset(
    {
        ".venv",
        "__pycache__",
        "node_modules",
        ".git",
        ".tox",
        ".nox",
        "dist",
        "build",
        ".eggs",
    }
)


@dataclass
class Package:
    """Represents a discovered package in the monorepo."""

    name: str
    path: Path
    has_tests: bool
    pyproject_path: Path


def _parse_package_name(pyproject_path: Path) -> Optional[str]:
    """Extract package name from pyproject.toml [project].name field.

    Returns None if the file cannot be parsed or doesn't have [project].name.
    """
    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("name")
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _has_test_directory(package_path: Path) -> bool:
    """Check if package has a tests/ or test/ directory."""
    return (package_path / "tests").is_dir() or (package_path / "test").is_dir()


def _should_skip_dir(dirname: str) -> bool:
    """Check if directory should be skipped during discovery."""
    return dirname in SKIP_DIRS or dirname.startswith(".")


def find_packages(root: Optional[Path] = None) -> list[Package]:
    """Find all packages with pyproject.toml in subdirectories.

    Recursively searches for pyproject.toml files in subdirectories,
    excluding the root directory. Returns a list of Package objects
    with package metadata.

    Args:
        root: Root directory to search from. Defaults to current working directory.

    Returns:
        List of Package objects found in the monorepo.
    """
    if root is None:
        root = Path.cwd()
    root = root.resolve()

    packages: list[Package] = []

    def _scan_directory(directory: Path) -> None:
        """Recursively scan directory for packages."""
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if not entry.is_dir():
                continue

            if _should_skip_dir(entry.name):
                continue

            pyproject_path = entry / "pyproject.toml"
            if pyproject_path.is_file():
                # Found a package
                name = _parse_package_name(pyproject_path)
                if name is None:
                    # Fallback to directory name
                    name = entry.name

                packages.append(
                    Package(
                        name=name,
                        path=entry,
                        has_tests=_has_test_directory(entry),
                        pyproject_path=pyproject_path,
                    )
                )

            # Continue scanning subdirectories
            _scan_directory(entry)

    _scan_directory(root)

    # Sort packages by name for consistent output
    packages.sort(key=lambda p: p.name)

    return packages
