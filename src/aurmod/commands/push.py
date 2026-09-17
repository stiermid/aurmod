"""Publish packages to the AUR in two steps."""

from __future__ import annotations

from pathlib import Path

import click
from git.exc import GitCommandError

from ..pkg import REGENERATE_MSG, get_pkgbase, get_version, srcinfo_status
from ..utils import (
    current_branch,
    get_root_repo,
    get_submodule,
    require_submodules,
    whitespace_issues,
)


def _blockers(root: str, name: str) -> list[str]:
    """Return publish blockers for one package (empty means pushable)."""
    from git.repo import Repo

    repo = Repo(root)
    sm = repo.submodules[name]
    pkg_dir = Path(root) / sm.path
    problems: list[str] = []

    if not (pkg_dir / "PKGBUILD").is_file():
        problems.append("missing PKGBUILD")
        return problems
    if not (pkg_dir / ".SRCINFO").is_file():
        problems.append("missing .SRCINFO")
        return problems

    base = get_pkgbase(pkg_dir)
    if base is None:
        problems.append("cannot read pkgbase from .SRCINFO")
    elif base != name:
        problems.append(
            f"folder {name!r} does not match pkgbase {base!r}; "
            f"rename the folder to {base!r}"
        )

    state, detail = srcinfo_status(pkg_dir)
    if state == "stale":
        problems.append(f".SRCINFO is stale; run: {REGENERATE_MSG}")
    elif state == "error":
        problems.append(f"cannot verify .SRCINFO: {detail}")

    try:
        sm_repo = sm.module()
    except ValueError:
        problems.append("submodule is not initialized")
        return problems

    if sm_repo.head.is_detached:
        problems.append(
            f"package is in detached HEAD; run: git -C {name} checkout master"
        )
    elif current_branch(sm_repo) != "master":
        problems.append(
            f"package is on {current_branch(sm_repo)!r}, "
            "expected 'master'; run: "
            f"git -C {name} checkout master"
        )

    if sm_repo.is_dirty(untracked_files=True):
        problems.append(
            f"package {name!r} has uncommitted changes; "
            f"commit inside {name} first"
        )

    ws = whitespace_issues(sm_repo)
    if ws:
        problems.append(f"whitespace errors:\n{ws}")
    return problems


def push_one(root: str, name: str) -> tuple[bool, str, str]:
    """Push one package; return ``(ok, version, message)``."""
    from git.repo import Repo

    repo = Repo(root)
    blockers = _blockers(root, name)
    if blockers:
        return False, "unknown", "; ".join(blockers)
    sm = repo.submodules[name]
    sm_repo = sm.module()
    try:
        sm_repo.git.push("origin", "master")
    except GitCommandError as exc:
        err = str(exc.stderr or exc) if hasattr(exc, "stderr") else str(exc)
        return False, "unknown", f"git push failed: {err.strip()}"
    try:
        repo.git.add(sm.path)
    except GitCommandError as exc:
        return False, "unknown", f"staging pointer failed: {exc}"
    version = get_version(Path(root) / sm.path)
    return True, version, "pushed"


@click.command()
@click.argument("pkgname", required=False, default=None)
@click.option(
    "--all",
    "all_packages",
    is_flag=True,
    help="Push every package in the collection.",
)
@click.option(
    "--commit",
    is_flag=True,
    help="Commit the outer pointer after pushing.",
)
def push(pkgname: str | None, all_packages: bool, commit: bool) -> None:
    """Push packages to the AUR, then stage the new outer pointer."""
    repo = get_root_repo()
    if all_packages:
        names = [sm.name for sm in require_submodules(repo)]
    elif pkgname:
        names = [get_submodule(repo, pkgname).name]
    else:
        raise click.ClickException("Specify a package or use --all.")

    assert repo.working_tree_dir is not None
    root = str(repo.working_tree_dir)
    ok: dict[str, str] = {}
    failed: dict[str, str] = {}
    for name in sorted(names):
        success, version, message = push_one(root, name)
        if success:
            ok[name] = version
            click.echo(f"{name}: pushed ({version})")
        else:
            failed[name] = message
            click.echo(f"{name}: refused: {message}")

    if ok:
        staged = repo.git.diff("--cached", "--name-only").strip()
        if not staged:
            click.echo("Outer pointer already up to date.")
        elif commit:
            if len(ok) == 1:
                (single, version) = next(iter(ok.items()))
                msg = f"{single}: {version}"
            else:
                msg = ", ".join(f"{n}: {v}" for n, v in sorted(ok.items()))
            repo.index.commit(msg)
            click.echo(f"Committed outer pointer: {msg}")
        else:
            if len(ok) == 1:
                (single, version) = next(iter(ok.items()))
                msg = f"{single}: {version}"
            else:
                msg = ", ".join(f"{n}: {v}" for n, v in sorted(ok.items()))
            click.echo("Outer pointer staged. Commit it with:")
            click.echo(f'  git commit -m "{msg}"')

    if failed:
        raise click.ClickException(
            f"Push failed for: {', '.join(sorted(failed))}"
        )
