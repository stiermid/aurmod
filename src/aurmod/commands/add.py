"""Add a package to worktree as submodule.

This module provides the ``add`` CLI command.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import click
from git import Repo, Submodule
from git.exc import GitCommandError

from ..pkg import (
    is_valid_aur_name,
    pkgbuild_template,
    run_printsrcinfo,
    srcinfo_template,
)
from ..utils import get_root_repo

AUR_URL = "ssh://aur@aur.archlinux.org/{pkgname}.git"


def _set_submodule_url(repo: Repo, pkgname: str, url: str) -> None:
    """Point a submodule and its origin remote at ``url``."""
    repo.git.config("-f", ".gitmodules", f"submodule.{pkgname}.url", url)
    try:
        repo.git.config(f"submodule.{pkgname}.url", url)
    except GitCommandError:
        pass
    try:
        sm = repo.submodules[pkgname]
        if sm.module_exists():
            sm.module().remotes.origin.set_url(url)
    except IndexError, AttributeError, ValueError, GitCommandError:
        pass


def _add_empty(pkgname: str, repo: Repo) -> None:
    """Create a new package folder offline and register it."""
    assert repo.working_tree_dir is not None
    dest = Path(repo.working_tree_dir) / pkgname
    if dest.exists():
        raise click.ClickException(f"Path {pkgname} already exists.")

    tmpdir = tempfile.mkdtemp(prefix=f"aurmod-{pkgname}-")
    try:
        seed = Path(tmpdir) / pkgname
        seed_repo = Repo.init(seed, initial_branch="master")
        (seed / "PKGBUILD").write_text(
            pkgbuild_template(pkgname), encoding="utf-8"
        )
        generated, _ = run_printsrcinfo(seed)
        if generated is not None:
            (seed / ".SRCINFO").write_text(generated, encoding="utf-8")
        else:
            (seed / ".SRCINFO").write_text(
                srcinfo_template(pkgname), encoding="utf-8"
            )
        seed_repo.git.add("PKGBUILD", ".SRCINFO")
        seed_repo.index.commit("initial commit")

        try:
            new_sm = Submodule.add(
                repo,
                name=pkgname,
                path=pkgname,
                url=f"file://{seed}",
                branch="master",
            )
        except (GitCommandError, ValueError) as exc:
            raise click.ClickException(f"Adding submodule: {exc}")

        aur_url = AUR_URL.format(pkgname=pkgname)
        _set_submodule_url(repo, pkgname, aur_url)
        assert repo.working_tree_dir is not None
        # Remove the tormentor: the seed is no longer needed once
        # the submodule has been cloned; origin now points at AUR.
        repo.git.add(".gitmodules", pkgname)
        repo.index.commit(f"addpkg: {pkgname}")
        click.echo(f"Successfully added: {new_sm.name}")
        click.echo("Fill in PKGBUILD, then: aurmod push " + pkgname)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        # Submodule.add clones from the seed; stray files on failure
        # should not linger in the worktree.
        if repo.is_dirty(untracked_files=True):
            stray = Path(repo.working_tree_dir) / pkgname
            if stray.exists() and not (stray / ".git").exists():
                if stray.is_dir() and not os.listdir(stray):
                    shutil.rmtree(stray, ignore_errors=True)


@click.command()
@click.argument("pkgname")
@click.option(
    "--empty",
    is_flag=True,
    help="Create a new package offline instead of cloning.",
)
def add(pkgname: str, empty: bool) -> None:
    """Add a package to worktree as submodule."""
    if not is_valid_aur_name(pkgname):
        raise click.ClickException(
            f"Invalid package name {pkgname!r}: use lowercase "
            "letters, digits and @._+- ."
        )
    repo = get_root_repo()

    sms = repo.submodules  # submodules

    if any(sm.name == pkgname for sm in sms):
        raise click.ClickException(f"Package {pkgname} is already in repo.")

    if empty:
        _add_empty(pkgname, repo)
        return

    try:
        new_sm = Submodule.add(
            repo,
            name=pkgname,
            path=pkgname,
            url=AUR_URL.format(pkgname=pkgname),
            branch="master",
        )
    except GitCommandError as e:
        raise click.ClickException(f"Adding submodule: {e}")
    except ValueError:
        repo.index.reset(head=True, working_tree=True)
        repo.git.clean("-ff", "-d")
        raise click.ClickException(f"Make sure package {pkgname} exists.")

    try:
        repo.git.add(".gitmodules", pkgname)
        repo.index.write()
        repo.index.commit(f"addpkg: {pkgname}")
        click.echo(f"Successfully added: {new_sm.name}")
    except GitCommandError as e:
        raise click.ClickException(f"Committing changes: {e}")
