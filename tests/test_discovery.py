"""Tests for package discovery."""

import pytest
from pathlib import Path

from uvtest.discovery import (
    Package,
    find_packages,
    _parse_package_name,
    _has_test_directory,
    _should_skip_dir,
    SKIP_DIRS,
)


class TestShouldSkipDir:
    """Tests for _should_skip_dir function."""

    def test_skips_venv(self):
        assert _should_skip_dir(".venv") is True

    def test_skips_pycache(self):
        assert _should_skip_dir("__pycache__") is True

    def test_skips_node_modules(self):
        assert _should_skip_dir("node_modules") is True

    def test_skips_git(self):
        assert _should_skip_dir(".git") is True

    def test_skips_hidden_dirs(self):
        assert _should_skip_dir(".hidden") is True
        assert _should_skip_dir(".mypy_cache") is True

    def test_allows_normal_dirs(self):
        assert _should_skip_dir("packages") is False
        assert _should_skip_dir("src") is False
        assert _should_skip_dir("libs") is False


class TestHasTestDirectory:
    """Tests for _has_test_directory function."""

    def test_detects_tests_dir(self, tmp_path: Path):
        (tmp_path / "tests").mkdir()
        assert _has_test_directory(tmp_path) is True

    def test_detects_test_dir(self, tmp_path: Path):
        (tmp_path / "test").mkdir()
        assert _has_test_directory(tmp_path) is True

    def test_no_test_dir(self, tmp_path: Path):
        assert _has_test_directory(tmp_path) is False

    def test_test_file_not_dir(self, tmp_path: Path):
        (tmp_path / "tests").write_text("")  # File, not directory
        assert _has_test_directory(tmp_path) is False


class TestParsePackageName:
    """Tests for _parse_package_name function."""

    def test_parses_valid_pyproject(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "my-package"')
        assert _parse_package_name(pyproject) == "my-package"

    def test_returns_none_for_missing_project_section(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[build-system]\nrequires = ["hatchling"]')
        assert _parse_package_name(pyproject) is None

    def test_returns_none_for_missing_name(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.0.0"')
        assert _parse_package_name(pyproject) is None

    def test_returns_none_for_invalid_toml(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("this is not valid toml [[[")
        assert _parse_package_name(pyproject) is None

    def test_returns_none_for_missing_file(self, tmp_path: Path):
        pyproject = tmp_path / "nonexistent.toml"
        assert _parse_package_name(pyproject) is None


class TestFindPackages:
    """Tests for find_packages function."""

    def test_finds_package_with_project_name(self, tmp_path: Path):
        # Create a package with pyproject.toml
        pkg_dir = tmp_path / "my-package"
        pkg_dir.mkdir()
        (pkg_dir / "pyproject.toml").write_text('[project]\nname = "my-package"')

        packages = find_packages(tmp_path)

        assert len(packages) == 1
        assert packages[0].name == "my-package"
        assert packages[0].path == pkg_dir
        assert packages[0].has_tests is False
        assert packages[0].pyproject_path == pkg_dir / "pyproject.toml"

    def test_falls_back_to_directory_name(self, tmp_path: Path):
        pkg_dir = tmp_path / "fallback-pkg"
        pkg_dir.mkdir()
        # No [project].name in pyproject.toml
        (pkg_dir / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["hatchling"]'
        )

        packages = find_packages(tmp_path)

        assert len(packages) == 1
        assert packages[0].name == "fallback-pkg"

    def test_detects_tests_directory(self, tmp_path: Path):
        pkg_dir = tmp_path / "tested-pkg"
        pkg_dir.mkdir()
        (pkg_dir / "pyproject.toml").write_text('[project]\nname = "tested-pkg"')
        (pkg_dir / "tests").mkdir()

        packages = find_packages(tmp_path)

        assert len(packages) == 1
        assert packages[0].has_tests is True

    def test_detects_test_directory(self, tmp_path: Path):
        pkg_dir = tmp_path / "tested-pkg"
        pkg_dir.mkdir()
        (pkg_dir / "pyproject.toml").write_text('[project]\nname = "tested-pkg"')
        (pkg_dir / "test").mkdir()

        packages = find_packages(tmp_path)

        assert len(packages) == 1
        assert packages[0].has_tests is True

    def test_excludes_root_pyproject(self, tmp_path: Path):
        # Root pyproject.toml should be excluded
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "root"')

        packages = find_packages(tmp_path)

        assert len(packages) == 0

    def test_finds_nested_packages(self, tmp_path: Path):
        # Create nested package structure
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()

        pkg1 = packages_dir / "pkg1"
        pkg1.mkdir()
        (pkg1 / "pyproject.toml").write_text('[project]\nname = "pkg1"')

        pkg2 = packages_dir / "pkg2"
        pkg2.mkdir()
        (pkg2 / "pyproject.toml").write_text('[project]\nname = "pkg2"')

        packages = find_packages(tmp_path)

        assert len(packages) == 2
        names = {p.name for p in packages}
        assert names == {"pkg1", "pkg2"}

    def test_skips_venv_directory(self, tmp_path: Path):
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        pkg_in_venv = venv_dir / "site-packages" / "some-pkg"
        pkg_in_venv.mkdir(parents=True)
        (pkg_in_venv / "pyproject.toml").write_text('[project]\nname = "hidden"')

        packages = find_packages(tmp_path)

        assert len(packages) == 0

    def test_skips_node_modules(self, tmp_path: Path):
        nm_dir = tmp_path / "node_modules"
        nm_dir.mkdir()
        pkg_in_nm = nm_dir / "some-pkg"
        pkg_in_nm.mkdir()
        (pkg_in_nm / "pyproject.toml").write_text('[project]\nname = "hidden"')

        packages = find_packages(tmp_path)

        assert len(packages) == 0

    def test_skips_pycache(self, tmp_path: Path):
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        # This would be unusual but we should still skip it
        (cache_dir / "pyproject.toml").write_text('[project]\nname = "hidden"')

        packages = find_packages(tmp_path)

        assert len(packages) == 0

    def test_skips_git_directory(self, tmp_path: Path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "pyproject.toml").write_text('[project]\nname = "hidden"')

        packages = find_packages(tmp_path)

        assert len(packages) == 0

    def test_returns_sorted_packages(self, tmp_path: Path):
        # Create packages in random order
        for name in ["zeta", "alpha", "mango"]:
            pkg = tmp_path / name
            pkg.mkdir()
            (pkg / "pyproject.toml").write_text(f'[project]\nname = "{name}"')

        packages = find_packages(tmp_path)

        names = [p.name for p in packages]
        assert names == ["alpha", "mango", "zeta"]

    def test_handles_invalid_pyproject(self, tmp_path: Path):
        pkg_dir = tmp_path / "broken-pkg"
        pkg_dir.mkdir()
        (pkg_dir / "pyproject.toml").write_text("this is [[[ not valid toml")

        # Should still find the package with directory name fallback
        packages = find_packages(tmp_path)

        assert len(packages) == 1
        assert packages[0].name == "broken-pkg"

    def test_uses_cwd_by_default(self, tmp_path: Path, monkeypatch):
        pkg_dir = tmp_path / "cwd-pkg"
        pkg_dir.mkdir()
        (pkg_dir / "pyproject.toml").write_text('[project]\nname = "cwd-pkg"')

        monkeypatch.chdir(tmp_path)
        packages = find_packages()  # No argument

        assert len(packages) == 1
        assert packages[0].name == "cwd-pkg"

    def test_finds_deeply_nested_packages(self, tmp_path: Path):
        # Create deeply nested structure
        deep = tmp_path / "level1" / "level2" / "level3"
        deep.mkdir(parents=True)
        (deep / "pyproject.toml").write_text('[project]\nname = "deep-pkg"')

        packages = find_packages(tmp_path)

        assert len(packages) == 1
        assert packages[0].name == "deep-pkg"

    def test_multiple_packages_mixed_test_status(self, tmp_path: Path):
        # Package with tests
        pkg1 = tmp_path / "with-tests"
        pkg1.mkdir()
        (pkg1 / "pyproject.toml").write_text('[project]\nname = "with-tests"')
        (pkg1 / "tests").mkdir()

        # Package without tests
        pkg2 = tmp_path / "without-tests"
        pkg2.mkdir()
        (pkg2 / "pyproject.toml").write_text('[project]\nname = "without-tests"')

        packages = find_packages(tmp_path)

        pkg_map = {p.name: p for p in packages}
        assert pkg_map["with-tests"].has_tests is True
        assert pkg_map["without-tests"].has_tests is False
