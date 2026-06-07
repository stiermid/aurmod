"""Add a package to worktree as submodule.

This module provides the ``add`` CLI command.
"""

import click
from git import InvalidGitRepositoryError, Repo, Submodule
from git.cmd import GitCommandError

from ..utils import is_submodule


@click.command()
@click.argument("pkgname")
def add(pkgname: str) -> None:
    """Add a package to worktree as submodule."""
    try:
        repo = Repo(".")
    except InvalidGitRepositoryError:
        raise click.ClickException("git repo is not found")

    if is_submodule(repo):
        repo = Repo("..")

    # repo = RootModule(repo)
    sms = repo.submodules  # submodules

    if any(sm.name == pkgname for sm in sms):
        raise click.ClickException(f"package {pkgname} is already in repo")

    try:
        new_sm = Submodule.add(
            repo,
            name=pkgname,
            path=pkgname,
            url=f"ssh://aur@aur.archlinux.org/{pkgname}.git",
        )
    except GitCommandError as e:
        print(f"Error adding submodule: {e}")

    try:
        repo.index.add([".gitmodules", pkgname])
        repo.index.write()
        repo.index.commit(f"addpkg: {pkgname}")
        click.echo(f"succesfully added {new_sm.name}")
    except GitCommandError as e:
        print(f"Error commiting changes: {e}")
