"""Sync packages in worktree.

This module provides the ``sync`` CLI command.
"""

import click

from ..utils import get_root_repo


@click.command()
@click.argument("pkgname", required=False, default=None)
def sync(pkgname: str) -> None:
    """Sync packages as submodule."""
    repo = get_root_repo()

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
