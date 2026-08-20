"""Sync packages in worktree.

This module provides the ``sync`` CLI command.
"""

import click

from ..messages import describe_package, read_srcinfo
from ..utils import get_root_repo, update_submodule


@click.command()
@click.argument("pkgname", required=False, default=None)
def sync(pkgname: str) -> None:
    """Sync packages as submodule."""
    repo = get_root_repo()

    sms = repo.submodules  # submodules

    if pkgname:
        try:
            sm = sms[pkgname]
        except IndexError:
            raise click.ClickException(f"Package {pkgname} is not in repo.")

        update_submodule(repo, sm)

        if repo.is_dirty(untracked_files=False):
            message = "syncpkg: " + describe_package(
                sm.name, read_srcinfo(sm.module())
            )
            repo.index.commit(message)

    else:
        updated = []
        for sm in sms:
            if update_submodule(repo, sm):
                updated.append(
                    describe_package(sm.name, read_srcinfo(sm.module()))
                )

        if updated:
            repo.index.commit("syncpkg: " + ", ".join(updated))
