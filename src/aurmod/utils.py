"""Utils."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click
from click import ClickException
from git import InvalidGitRepositoryError
from git.repo import Repo

if TYPE_CHECKING:
    from git import Submodule
    from git.types import PathLike


def is_submodule(repo: Repo) -> bool:
    """Check whether repo is submodule or not.

    A submodule has a ``.git`` gitfile whose gitdir lives under the
    parent repo's ``.git/modules/`` directory (linked worktrees live
    under ``.git/worktrees/`` instead).
    """
    expected_git_dir = os.path.join(str(repo.working_tree_dir), ".git")
    marker = os.path.join(".git", "modules")
    return os.path.isfile(expected_git_dir) and marker in str(repo.git_dir)


def get_root_repo(path: PathLike = ".") -> Repo:
    """Get the root git repository, stepping up if inside a submodule."""
    try:
        repo = Repo(path)
    except InvalidGitRepositoryError:
        raise ClickException("Git repo is not found.")

    return Repo("..") if is_submodule(repo) else repo


def update_submodule(repo: Repo, sm: Submodule) -> bool:
    """Pull latest changes for a submodule and stage the updated gitlink.

    Returns ``True`` if the submodule's checked-out commit changed.
    """
    click.echo(f"Pulling latest remote changes for: {sm.name}")
    old_commit = str(sm.module().head.commit) if sm.module_exists() else None
    sm.update(init=True)
    sm_repo = sm.module()
    origin = sm_repo.remotes.origin
    origin.pull()
    repo.git.add([sm.path])
    return old_commit != str(sm_repo.head.commit)
