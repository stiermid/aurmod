"""Bring AUR changes into package folders."""

from __future__ import annotations

from pathlib import Path

import click
from git.exc import GitCommandError

from ..pkg import get_version
from ..utils import (
    fetch_origin,
    get_root_repo,
    get_submodule,
    is_ancestor,
    require_submodules,
)


def _stage_pointer(repo, sm) -> str | None:
    """Stage the outer gitlink for ``sm``; return error or ``None``."""
    try:
        repo.git.add(sm.path)
    except GitCommandError as exc:
        return f"staging pointer failed: {exc}"
    return None


def pull_one(root: str, name: str) -> tuple[bool, str, str]:
    """Pull one package; return ``(ok, version, message)``.

    On a successful fast-forward (or when already in sync with the
    remote) the outer pointer is staged, mirroring ``push``.
    """
    from git.repo import Repo

    repo = Repo(root)
    try:
        sm = repo.submodules[name]
    except IndexError:
        return False, "unknown", f"Package {name} is not in repo."
    if not sm.module_exists():
        try:
            sm.update(init=True)
        except GitCommandError as exc:
            return False, "unknown", f"init failed: {exc}"
    sm_repo = sm.module()

    if sm_repo.head.is_detached:
        try:
            sm_repo.git.checkout("master")
        except GitCommandError as exc:
            return False, "unknown", f"cannot repair detached HEAD: {exc}"
        click.echo(f"{name}: repaired detached HEAD (now on master)")

    try:
        branch = sm_repo.active_branch.name
    except ValueError, TypeError:
        return (
            False,
            "unknown",
            f"still detached; run: git -C {name} checkout master",
        )
    if branch != "master":
        try:
            sm_repo.git.checkout("master")
        except GitCommandError as exc:
            return False, "unknown", f"cannot checkout master: {exc}"
        click.echo(f"{name}: switched to master")

    if not fetch_origin(sm_repo):
        return False, "unknown", "fetch failed"
    try:
        sm_repo.git.rev_parse("--verify", "origin/master")
    except GitCommandError:
        return True, "unknown", "no upstream yet"

    head = str(sm_repo.head.commit.hexsha)
    remote = str(sm_repo.git.rev_parse("origin/master").strip())
    if head == remote:
        err = _stage_pointer(repo, sm)
        if err is not None:
            return False, "unknown", err
        version = get_version(Path(root) / sm.path)
        return True, version, "already up to date"
    if is_ancestor(sm_repo, head, remote):
        try:
            sm_repo.git.merge("--ff-only", "origin/master")
        except GitCommandError as exc:
            return False, "unknown", f"fast-forward failed: {exc}"
        err = _stage_pointer(repo, sm)
        if err is not None:
            return False, "unknown", err
        version = get_version(Path(root) / sm.path)
        return True, version, "fast-forwarded"
    if is_ancestor(sm_repo, remote, head):
        version = get_version(Path(root) / sm.path)
        return True, version, "ahead of AUR; push to publish"
    return (
        False,
        "unknown",
        (
            "diverged from AUR; merge inside the package folder: "
            f"git -C {name} merge origin/master"
        ),
    )


@click.command()
@click.argument("pkgname", required=False, default=None)
@click.option(
    "--all",
    "all_packages",
    is_flag=True,
    help="Pull every package in the collection.",
)
@click.option(
    "--commit",
    is_flag=True,
    help="Commit the outer pointer after pulling.",
)
def pull(pkgname: str | None, all_packages: bool, commit: bool) -> None:
    """Pull AUR changes into package folders, then stage the pointer."""
    repo = get_root_repo()
    if all_packages:
        names = [sm.name for sm in require_submodules(repo)]
    elif pkgname:
        names = [get_submodule(repo, pkgname).name]
    else:
        raise click.ClickException("Specify a package or use --all.")

    assert repo.working_tree_dir is not None
    root = str(repo.working_tree_dir)
    updated: dict[str, str] = {}
    failed: dict[str, str] = {}
    for name in sorted(names):
        ok, version, message = pull_one(root, name)
        click.echo(f"{name}: {message}")
        if not ok:
            failed[name] = message
        elif message in ("fast-forwarded", "already up to date"):
            updated[name] = version

    if updated:
        staged = repo.git.diff("--cached", "--name-only").strip()
        if not staged:
            click.echo("Outer pointer already up to date.")
        elif commit:
            if len(updated) == 1:
                (single, version) = next(iter(updated.items()))
                msg = f"{single}: {version}"
            else:
                msg = ", ".join(f"{n}: {v}" for n, v in sorted(updated.items()))
            repo.index.commit(msg)
            click.echo(f"Committed outer pointer: {msg}")
        else:
            if len(updated) == 1:
                (single, version) = next(iter(updated.items()))
                msg = f"{single}: {version}"
            else:
                msg = ", ".join(f"{n}: {v}" for n, v in sorted(updated.items()))
            click.echo("Outer pointer staged. Commit it with:")
            click.echo(f'  git commit -m "{msg}"')

    if failed:
        raise click.ClickException(
            f"Pull failed for: {', '.join(sorted(failed))}"
        )
