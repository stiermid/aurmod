"""Show the history of a single package."""

from __future__ import annotations

import click
from git.exc import GitCommandError

from ..utils import get_root_repo, get_submodule


@click.command(
    context_settings={"ignore_unknown_options": True},
)
@click.argument("pkgname")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def log(pkgname: str, args: tuple[str, ...]) -> None:
    """Show the git history of just one package folder."""
    repo = get_root_repo()
    sm = get_submodule(repo, pkgname)
    if not sm.module_exists():
        raise click.ClickException(f"Package {pkgname} is not initialized.")
    sm_repo = sm.module()
    git_args = list(args) if args else ["--oneline", "-20"]
    try:
        out = sm_repo.git.log(*git_args)
    except GitCommandError as exc:
        raise click.ClickException(f"git log failed: {exc}")
    if out:
        click.echo(out)
