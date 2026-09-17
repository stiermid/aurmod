"""Bring AUR changes into package folders."""

from __future__ import annotations

import click
from git.exc import GitCommandError

from ..utils import (
    fetch_origin,
    get_root_repo,
    get_submodule,
    is_ancestor,
    require_submodules,
)


def pull_one(root: str, name: str) -> tuple[bool, str]:
    """Pull one package; return ``(ok, message)``."""
    from git.repo import Repo

    repo = Repo(root)
    try:
        sm = repo.submodules[name]
    except IndexError:
        return False, f"Package {name} is not in repo."
    if not sm.module_exists():
        try:
            sm.update(init=True)
        except GitCommandError as exc:
            return False, f"init failed: {exc}"
    sm_repo = sm.module()

    if sm_repo.head.is_detached:
        try:
            sm_repo.git.checkout("master")
        except GitCommandError as exc:
            return False, f"cannot repair detached HEAD: {exc}"
        click.echo(f"{name}: repaired detached HEAD (now on master)")

    try:
        branch = sm_repo.active_branch.name
    except ValueError, TypeError:
        return False, f"still detached; run: git -C {name} checkout master"
    if branch != "master":
        try:
            sm_repo.git.checkout("master")
        except GitCommandError as exc:
            return False, f"cannot checkout master: {exc}"
        click.echo(f"{name}: switched to master")

    if not fetch_origin(sm_repo):
        return False, "fetch failed"
    try:
        sm_repo.git.rev_parse("--verify", "origin/master")
    except GitCommandError:
        return True, "no upstream yet"

    head = str(sm_repo.head.commit.hexsha)
    remote = str(sm_repo.git.rev_parse("origin/master").strip())
    if head == remote:
        return True, "already up to date"
    if is_ancestor(sm_repo, head, remote):
        try:
            sm_repo.git.merge("--ff-only", "origin/master")
        except GitCommandError as exc:
            return False, f"fast-forward failed: {exc}"
        return True, "fast-forwarded"
    if is_ancestor(sm_repo, remote, head):
        return True, "ahead of AUR; push to publish"
    return False, (
        "diverged from AUR; merge inside the package folder: "
        f"git -C {name} merge origin/master"
    )


@click.command()
@click.argument("pkgname", required=False, default=None)
@click.option(
    "--all",
    "all_packages",
    is_flag=True,
    help="Pull every package in the collection.",
)
def pull(pkgname: str | None, all_packages: bool) -> None:
    """Pull AUR changes into package folders (fast-forward only)."""
    repo = get_root_repo()
    if all_packages:
        names = [sm.name for sm in require_submodules(repo)]
    elif pkgname:
        names = [get_submodule(repo, pkgname).name]
    else:
        raise click.ClickException("Specify a package or use --all.")

    assert repo.working_tree_dir is not None
    root = str(repo.working_tree_dir)
    failed: dict[str, str] = {}
    for name in sorted(names):
        ok, message = pull_one(root, name)
        click.echo(f"{name}: {message}")
        if not ok:
            failed[name] = message
    if failed:
        raise click.ClickException(
            f"Pull failed for: {', '.join(sorted(failed))}"
        )
