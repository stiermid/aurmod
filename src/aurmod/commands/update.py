"""Update a package and commit in both repositories."""

from __future__ import annotations

import click

from ..checks import IntegrityError, check_level, verify_package
from ..messages import describe_package, read_srcinfo
from ..utils import get_root_repo


@click.command()
@click.argument("pkgname")
@click.option(
    "-m",
    "--message",
    default=None,
    help="Override the generated commit message.",
)
def update(pkgname: str, message: str | None) -> None:
    """Update a package and commit in both repositories."""
    repo = get_root_repo()

    try:
        sm = repo.submodules[pkgname]
    except IndexError:
        raise click.ClickException(f"Package {pkgname} is not in repo.")

    if not sm.module_exists():
        raise click.ClickException(f"Package {pkgname} is not checked out.")
    sm_repo = sm.module()

    if not sm_repo.is_dirty(untracked_files=True):
        raise click.ClickException(
            f"No changes to commit for package {pkgname}."
        )

    try:
        verify_package(sm_repo, level=check_level(repo))
    except IntegrityError as e:
        raise click.ClickException(str(e))

    sm_repo.git.add("-A")
    if message is None:
        message = "upgpkg: " + describe_package(sm.name, read_srcinfo(sm_repo))

    sm_repo.index.commit(message, skip_hooks=True)
    repo.git.add(sm.path)
    repo.index.commit(message, skip_hooks=True)
    click.echo(f"Successfully updated: {message}")
