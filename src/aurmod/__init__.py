"""aurmod is a tool for managing aur packages using git submodules."""

from .cli import cli


def main() -> None:
    """Entry point for the app."""
    cli()
