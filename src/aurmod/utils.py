"""Utils."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from click import ClickException
from git import InvalidGitRepositoryError
from git.repo import Repo

if TYPE_CHECKING:
    from git.types import PathLike


def is_submodule(repo: Repo) -> bool:
    """Check whether repo is submodule or not."""
    expected_git_dir = os.path.join(str(repo.working_tree_dir), ".git")
    git_dir_str = str(repo.git_dir)
    return os.path.isfile(expected_git_dir) or "modules" in git_dir_str


def get_root_repo(path: PathLike = ".") -> Repo:
    """Get the root git repository, stepping up if inside a submodule."""
    try:
        repo = Repo(path)
    except InvalidGitRepositoryError:
        raise ClickException("Git repo is not found.")

    return Repo("..") if is_submodule(repo) else repo
