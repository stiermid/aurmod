"""Utils."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import git


def is_submodule(repo: git.Repo) -> bool:
    """Check whether repo is submodule or not."""
    expected_git_dir = os.path.join(str(repo.working_tree_dir), ".git")
    git_dir_str = str(repo.git_dir)
    return os.path.isfile(expected_git_dir) or "modules" in git_dir_str
