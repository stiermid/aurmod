"""Tests for :mod:`aurmod.utils`."""

from __future__ import annotations

import click
import pytest
from helpers import cwd_context

from aurmod.utils import (
    ahead_behind,
    current_branch,
    get_root_repo,
    get_submodule,
    is_submodule,
    pointer_state,
    require_submodules,
)


def test_is_submodule_false_on_plain_repo(repo_factory) -> None:
    """A normal repository is not a submodule."""
    repo = repo_factory()
    assert is_submodule(repo) is False


def test_is_submodule_true_on_submodule(submodule_factory) -> None:
    """A repository created as a git submodule is recognized."""
    worktree, _ = submodule_factory("pkg-a")
    sm_repo = worktree.submodules["pkg-a"].module()
    assert is_submodule(sm_repo) is True


def test_get_root_repo_returns_self_at_root(repo_factory) -> None:
    """At the root, get_root_repo returns the repository itself."""
    repo = repo_factory()
    root = get_root_repo(str(repo.working_tree_dir))
    assert str(root.working_tree_dir) == str(repo.working_tree_dir)


def test_get_root_repo_returns_parent_inside_submodule(
    submodule_factory,
) -> None:
    """Inside a submodule, get_root_repo resolves to the parent worktree."""
    worktree, _ = submodule_factory("pkg-a")
    sm_dir = str(worktree.submodules["pkg-a"].module().working_tree_dir)
    with cwd_context(sm_dir):
        root = get_root_repo()
    assert str(root.working_tree_dir) == str(worktree.working_tree_dir)


def test_get_root_repo_raises_outside_git_repo(tmp_path) -> None:
    """Outside any git repository get_root_repo raises ClickException."""
    with pytest.raises(click.ClickException, match=r"Git repo is not found\."):
        get_root_repo(str(tmp_path))


def test_get_submodule_unknown(submodule_factory) -> None:
    """Requesting an unknown package raises a clear error."""
    worktree, _ = submodule_factory("pkg-a")
    with pytest.raises(click.ClickException, match="ghost"):
        get_submodule(worktree, "ghost")


def test_require_submodules_empty(repo_factory) -> None:
    """An empty collection raises a clear error."""
    repo = repo_factory()
    with pytest.raises(click.ClickException, match="No packages"):
        require_submodules(repo)


def test_pointer_state_ok(submodule_factory) -> None:
    """A fresh submodule pointer is in sync."""
    worktree, _ = submodule_factory("pkg-a")
    sm = worktree.submodules["pkg-a"]
    assert pointer_state(worktree, sm)["state"] == "ok"


def test_ahead_behind_up_to_date(submodule_factory) -> None:
    """A fresh clone is neither ahead nor behind."""
    worktree, _ = submodule_factory("pkg-a")
    sm_repo = worktree.submodules["pkg-a"].module()
    assert ahead_behind(sm_repo) == (0, 0)


def test_current_branch_master(submodule_factory) -> None:
    """Submodules are checked out on master by default."""
    worktree, _ = submodule_factory("pkg-a")
    sm_repo = worktree.submodules["pkg-a"].module()
    assert current_branch(sm_repo) == "master"
