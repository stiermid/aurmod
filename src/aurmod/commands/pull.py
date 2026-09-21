"""Bring AUR changes into package folders."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click
from git.exc import GitCommandError

from ..pkg import get_version
from ..utils import (
    commit_paths,
    fetch_origin,
    get_root_repo,
    get_submodule,
    is_ancestor,
    require_submodules,
    staged_sha,
)

if TYPE_CHECKING:
    from git import Repo, Submodule


def _stage_pointer(repo: Repo, sm: Submodule) -> str | None:
    """Stage the outer gitlink for ``sm``; return error or ``None``."""
    try:
        repo.git.add(sm.path)
    except GitCommandError as exc:
        return f"staging pointer failed: {exc}"
    return None


def _package_version(root: str, sm: Submodule, sm_repo: Repo) -> str:
    """Return ``pkgver-pkgrel`` for a package, or short SHA as fallback."""
    version = get_version(Path(root) / sm.path)
    if version == "unknown":
        version = sm_repo.head.commit.hexsha[:7]
    return version


def pull_one(root: str, name: str) -> tuple[bool, str, str]:
    """Pull one package; return ``(ok, version, message)``.

    Fast-forward and already-in-sync paths stage the outer pointer;
    the caller decides which staged pointers to commit.
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
        return True, _package_version(root, sm, sm_repo), "already up to date"
    if is_ancestor(sm_repo, head, remote):
        try:
            sm_repo.git.merge("--ff-only", "origin/master")
        except GitCommandError as exc:
            return False, "unknown", f"fast-forward failed: {exc}"
        err = _stage_pointer(repo, sm)
        if err is not None:
            return False, "unknown", err
        return True, _package_version(root, sm, sm_repo), "fast-forwarded"
    if is_ancestor(sm_repo, remote, head):
        return (
            True,
            _package_version(root, sm, sm_repo),
            "ahead of AUR; push to publish",
        )
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
def pull(pkgname: str | None, all_packages: bool) -> None:
    """Pull AUR changes into package folders, then commit the pointer."""
    repo = get_root_repo()
    if all_packages:
        sms = require_submodules(repo)
    elif pkgname:
        sms = [get_submodule(repo, pkgname)]
    else:
        raise click.ClickException("Specify a package or use --all.")

    assert repo.working_tree_dir is not None
    root = str(repo.working_tree_dir)
    names = sorted(sm.name for sm in sms)
    paths = {sm.name: sm.path for sm in sms}
    before = {name: staged_sha(repo, paths[name]) for name in names}
    results: dict[str, str] = {}
    versions: dict[str, str] = {}
    failed: dict[str, str] = {}
    for name in names:
        ok, version, message = pull_one(root, name)
        click.echo(f"{name}: {message}")
        results[name] = message
        if not ok:
            failed[name] = message
        elif message in ("fast-forwarded", "already up to date"):
            versions[name] = version

    # Only pointers this pull actually updated are committed, so the
    # message names just those packages and unrelated staged changes
    # (e.g. a pointer staged by `push` without `--commit`) are left.
    updated = [
        name
        for name in names
        if name in versions and staged_sha(repo, paths[name]) != before[name]
    ]
    if updated:
        diff_paths = [paths[name] for name in updated]
        staged = set(
            repo.git.diff("--cached", "--name-only", "--", *diff_paths).split()
        )
        committable = [name for name in updated if paths[name] in staged]
        if committable:
            if len(committable) == 1:
                name = committable[0]
                msg = f"{name}: {versions[name]}"
            else:
                msg = ", ".join(f"{n}: {versions[n]}" for n in committable)
            commit_paths(repo, msg, [paths[name] for name in committable])
            click.echo(f"Committed outer pointer: {msg}")
        else:
            click.echo("Outer pointer already up to date.")
    elif not failed and all(
        message in ("already up to date", "no upstream yet")
        for message in results.values()
    ):
        click.echo("Outer pointer already up to date.")

    if failed:
        raise click.ClickException(
            f"Pull failed for: {', '.join(sorted(failed))}"
        )
