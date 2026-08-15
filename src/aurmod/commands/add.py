"""Add a package to worktree as submodule.

This module provides the ``add`` CLI command.
"""

import click
from git import Submodule
from git.exc import GitCommandError

from ..utils import get_root_repo

AUR_URL = "ssh://aur@aur.archlinux.org/{pkgname}.git"


@click.command()
@click.argument("pkgname")
def add(pkgname: str) -> None:
    """Add a package to worktree as submodule."""
    repo = get_root_repo()

    sms = repo.submodules  # submodules

    if any(sm.name == pkgname for sm in sms):
        raise click.ClickException(f"Package {pkgname} is already in repo.")

    try:
        new_sm = Submodule.add(
            repo,
            name=pkgname,
            path=pkgname,
            url=AUR_URL.format(pkgname=pkgname),
        )
    except GitCommandError as e:
        raise click.ClickException(f"Adding submodule: {e}")
    except ValueError:
        repo.index.reset(head=True, working_tree=True)
        repo.git.clean("-ff", "-d")
        raise click.ClickException(f"Make sure package {pkgname} exists.")

    try:
        repo.git.add(".gitmodules", pkgname)
        repo.index.write()
        repo.index.commit(f"addpkg: {pkgname}")
        click.echo(f"Successfully added: {new_sm.name}")
    except GitCommandError as e:
        raise click.ClickException(f"Committing changes: {e}")
