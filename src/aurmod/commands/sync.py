"""Sync packages in worktree.

This module provides the ``sync`` CLI command.
"""

import click
from git import InvalidGitRepositoryError, Repo

from ..utils import is_submodule


@click.command()
@click.argument("pkgname", required=False, default=None)
def sync(pkgname: str) -> None:
    """Sync packages as submodule."""
    try:
        repo = Repo(".")
    except InvalidGitRepositoryError:
        raise click.ClickException("Git repo is not found.")

    if is_submodule(repo):
        repo = Repo("..")

    sms = repo.submodules  # submodules

    if pkgname:
        sm = sms[pkgname]

        if not sm.exists():
            raise click.ClickException(f"Package {pkgname} is not in repo.")

        click.echo(f"Pulling latest remote changes for: {sm.name}")
        sm.update(init=True)
        sm_repo = sm.module()
        origin = sm_repo.remotes.origin
        origin.pull()

        repo.git.add([sm.path])

        if repo.is_dirty(untracked_files=False):
            repo.index.commit(f"syncpkg: {sm.name}")

    else:
        for sm in sms:
            click.echo(f"Pulling latest remote changes for: {sm.name}")
            sm.update(init=True)
            sm_repo = sm.module()
            origin = sm_repo.remotes.origin
            origin.pull()

            repo.git.add([sm.path])

            if repo.is_dirty(untracked_files=False):
                repo.index.commit(f"syncpkg: {sm.name}")
