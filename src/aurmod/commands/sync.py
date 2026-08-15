"""Sync packages in worktree.

This module provides the ``sync`` CLI command.
"""

import click

from ..utils import get_root_repo, update_submodule


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

        update_submodule(repo, sm)

        if repo.is_dirty(untracked_files=False):
            repo.index.commit(f"syncpkg: {sm.name}")

    else:
        updated = [sm.name for sm in sms if update_submodule(repo, sm)]

        if updated:
            repo.index.commit(f"syncpkg: {', '.join(updated)}")
