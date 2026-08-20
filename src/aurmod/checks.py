"""Package integrity checks run before committing."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import click
from git.exc import GitCommandError

if TYPE_CHECKING:
    from git import Repo

DEFAULT_LEVEL = "full"
LEVELS = ("off", "light", "full")


class IntegrityError(Exception):
    """Raised when a package fails an integrity check."""


def check_level(repo: Repo) -> str:
    """Return the ``aurmod.check`` level configured for the repository."""
    level = repo.config_reader().get_value("aurmod", "check", DEFAULT_LEVEL)
    if level not in LEVELS:
        raise click.ClickException(
            f"Invalid aurmod.check value '{level}'. "
            f"Choose from {', '.join(LEVELS)}."
        )
    return level


def has_makepkg() -> bool:
    """Return whether ``makepkg`` is available on the system."""
    return shutil.which("makepkg") is not None


def print_srcinfo_dir(workdir: Path) -> str | None:
    """Return freshly generated ``.SRCINFO`` content, or ``None``.

    ``None`` is returned when ``makepkg`` is unavailable or fails.
    """
    if not has_makepkg():
        return None
    result = subprocess.run(
        ["makepkg", "--printsrcinfo"],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def verify_package(repo: Repo, level: str | None = None) -> None:
    """Verify a package repository before committing.

    The ``full`` level requires ``makepkg``; when it is missing the check
    degrades to the ``light`` level with a warning. Raises
    :class:`IntegrityError` on fatal failures.
    """
    if level is None:
        level = check_level(repo)
    if level == "off":
        return

    _check_whitespace(repo)
    _check_structural(repo)

    if level == "light":
        return

    if not has_makepkg():
        click.echo(
            "Warning: makepkg not found; skipping .SRCINFO regeneration "
            "and source verification.",
            err=True,
        )
        return

    _regenerate_srcinfo(repo)
    _verify_sources(repo)


def _check_whitespace(repo: Repo) -> None:
    try:
        repo.git.diff("HEAD", "--check")
    except GitCommandError:
        click.echo("Warning: whitespace issues found in the package.", err=True)


def _check_structural(repo: Repo) -> None:
    if not Path(repo.working_tree_dir, "PKGBUILD").is_file():
        raise IntegrityError("PKGBUILD is missing from the package directory.")


def _regenerate_srcinfo(repo: Repo) -> None:
    content = print_srcinfo_dir(Path(repo.working_tree_dir))
    if content is None:
        raise IntegrityError("Could not generate .SRCINFO.")
    (Path(repo.working_tree_dir) / ".SRCINFO").write_text(
        content, encoding="utf-8"
    )
    repo.git.add(".SRCINFO")


def _verify_sources(repo: Repo) -> None:
    result = subprocess.run(
        ["makepkg", "--verifysource", "-f"],
        cwd=repo.working_tree_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise IntegrityError(
            "Source verification failed:\n" + result.stdout + result.stderr
        )
