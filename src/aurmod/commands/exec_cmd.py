"""Run a command inside package folders."""

from __future__ import annotations

import subprocess

import click

from ..utils import get_root_repo, get_submodule, require_submodules


@click.command(
    name="exec",
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
)
@click.option(
    "--all",
    "all_packages",
    is_flag=True,
    help="Run in every package folder.",
)
@click.argument("pkgname", required=False, default=None)
@click.argument("command", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def exec_cmd(
    ctx: click.Context,
    all_packages: bool,
    pkgname: str | None,
    command: tuple[str, ...],
) -> None:
    r"""Run any command inside package folders.

    Examples:
    \b
      aurmod exec --all -- git status --short
      aurmod exec foo -- makepkg --printsrcinfo

    """
    extra = tuple(ctx.args or ())
    full = tuple(command or ()) + extra
    # Strip a leading "--" left over from ``--`` separator handling.
    if full and full[0] == "--":
        full = full[1:]
    # With --all there is no PKGNAME slot, so click mis-assigns the
    # first command word to ``pkgname``; fold it back into the command.
    if all_packages and pkgname is not None:
        full = (pkgname, *full)
        pkgname = None
    if not full:
        raise click.ClickException("No command given. Use '-- <command>'.")

    repo = get_root_repo()
    if all_packages:
        names = [sm.name for sm in require_submodules(repo)]
    elif pkgname:
        names = [get_submodule(repo, pkgname).name]
    else:
        raise click.ClickException("Specify a package or use --all.")

    assert repo.working_tree_dir is not None
    import os

    failed: list[str] = []
    for name in sorted(names):
        sm = repo.submodules[name]
        assert repo.working_tree_dir is not None
        cwd = os.path.join(str(repo.working_tree_dir), sm.path)
        click.echo(f"==> {name} <==")
        proc = subprocess.run(list(full), cwd=cwd)
        if proc.returncode != 0:
            failed.append(name)
    if failed:
        raise click.ClickException(
            f"Command failed in: {', '.join(sorted(failed))}"
        )
