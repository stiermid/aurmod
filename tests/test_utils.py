"""Tests for :mod:`aurmod.utils`."""

from __future__ import annotations

import click
import pytest
from helpers import commit_file, cwd_context

from aurmod.utils import get_root_repo, is_submodule, update_submodule


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


def test_update_submodule_returns_false_when_up_to_date(
    submodule_factory,
) -> None:
    """update_submodule returns False when there is nothing to pull."""
    worktree, _ = submodule_factory("pkg-a")
    sm = worktree.submodules["pkg-a"]
    assert update_submodule(worktree, sm) is False
    assert worktree.is_dirty(untracked_files=False) is False


def test_update_submodule_pulls_and_stages_gitlink(submodule_factory) -> None:
    """update_submodule advances the submodule and stages the new gitlink."""
    worktree, sources = submodule_factory("pkg-a")
    commit_file(
        sources["pkg-a"], "PKGBUILD", "pkgname=pkg-a\npkgver=2\n", "bump"
    )

    sm = worktree.submodules["pkg-a"]
    assert update_submodule(worktree, sm) is True
    assert str(sm.module().head.commit) == str(sources["pkg-a"].head.commit)
    staged = worktree.git.diff("--cached", "--name-only")
    assert "pkg-a" in staged
