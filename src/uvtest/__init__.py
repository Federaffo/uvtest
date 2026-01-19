"""uvtest - A CLI tool to run pytest tests across all packages in a UV monorepo."""

try:
    from uvtest._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"
