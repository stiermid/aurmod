"""Tests for the ``sync`` command."""

from __future__ import annotations

from helpers import commit_file


def test_sync_specific_package(submodule_factory, cli_runner) -> None:
    """Syncing a named package updates it and creates a commit."""
    worktree, sources = submodule_factory("pkg-a")
    commit_file(
        sources["pkg-a"], "PKGBUILD", "pkgname=pkg-a\npkgver=2\n", "bump"
    )

    result = cli_runner(str(worktree.working_tree_dir), ["sync", "pkg-a"])

    assert result.exit_code == 0
    assert worktree.head.commit.message.strip() == "syncpkg: pkg-a"
    sm = worktree.submodules["pkg-a"]
    assert str(sm.module().head.commit) == str(sources["pkg-a"].head.commit)


def test_sync_unknown_package(submodule_factory, cli_runner) -> None:
    """Syncing a package that is not tracked fails."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["sync", "ghost"])

    assert result.exit_code == 1
    assert "Package ghost is not in repo." in result.output


def test_sync_specific_no_changes(submodule_factory, cli_runner) -> None:
    """Syncing an up-to-date package creates no commit."""
    worktree, _ = submodule_factory("pkg-a")
    before = worktree.head.commit.hexsha

    result = cli_runner(str(worktree.working_tree_dir), ["sync", "pkg-a"])

    assert result.exit_code == 0
    assert worktree.head.commit.hexsha == before


def test_sync_all_packages(submodule_factory, cli_runner) -> None:
    """Syncing everything commits a message listing all updated packages."""
    worktree, sources = submodule_factory("pkg-a", "pkg-b")
    commit_file(sources["pkg-a"], "PKGBUILD", "pkgver=2\n", "bump a")
    commit_file(sources["pkg-b"], "PKGBUILD", "pkgver=3\n", "bump b")

    result = cli_runner(str(worktree.working_tree_dir), ["sync"])

    assert result.exit_code == 0
    message = worktree.head.commit.message.strip()
    assert message.startswith("syncpkg:")
    assert "pkg-a" in message
    assert "pkg-b" in message


def test_sync_all_no_changes(submodule_factory, cli_runner) -> None:
    """Syncing everything with nothing to update creates no commit."""
    worktree, _ = submodule_factory("pkg-a")
    before = worktree.head.commit.hexsha

    result = cli_runner(str(worktree.working_tree_dir), ["sync"])

    assert result.exit_code == 0
    assert worktree.head.commit.hexsha == before
