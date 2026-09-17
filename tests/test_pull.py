"""Tests for the ``pull`` command."""

from __future__ import annotations

from helpers import commit_file


def test_pull_specific_package(submodule_factory, cli_runner) -> None:
    """Pulling a named package fast-forwards it without committing."""
    worktree, sources = submodule_factory("pkg-a")
    commit_file(
        sources["pkg-a"], "PKGBUILD", "pkgname=pkg-a\npkgver=2\n", "bump"
    )
    before = worktree.head.commit.hexsha

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "pkg-a"])

    assert result.exit_code == 0
    assert "fast-forwarded" in result.output
    sm = worktree.submodules["pkg-a"]
    assert str(sm.module().head.commit) == str(sources["pkg-a"].head.commit)
    # pull never touches the outer history: the pointer is now outdated.
    assert worktree.head.commit.hexsha == before


def test_pull_unknown_package(submodule_factory, cli_runner) -> None:
    """Pulling a package that is not tracked fails."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "ghost"])

    assert result.exit_code == 1
    assert "Package ghost is not in repo." in result.output


def test_pull_specific_no_changes(submodule_factory, cli_runner) -> None:
    """Pulling an up-to-date package reports it."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "pkg-a"])

    assert result.exit_code == 0
    assert "already up to date" in result.output


def test_pull_all_packages(submodule_factory, cli_runner) -> None:
    """Pulling everything updates all behind packages."""
    worktree, sources = submodule_factory("pkg-a", "pkg-b")
    commit_file(sources["pkg-a"], "PKGBUILD", "pkgver=2\n", "bump a")
    commit_file(sources["pkg-b"], "PKGBUILD", "pkgver=3\n", "bump b")

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "--all"])

    assert result.exit_code == 0
    for pkg in ("pkg-a", "pkg-b"):
        sm = worktree.submodules[pkg]
        assert str(sm.module().head.commit) == str(sources[pkg].head.commit)


def test_pull_repairs_detached(submodule_factory, cli_runner) -> None:
    """A detached package folder is checked back out to master."""
    worktree, _ = submodule_factory("pkg-a")
    sm_repo = worktree.submodules["pkg-a"].module()
    sm_repo.git.checkout("--detach", "HEAD")

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "pkg-a"])

    assert result.exit_code == 0
    assert "repaired detached HEAD" in result.output
    assert sm_repo.head.is_detached is False


def test_pull_diverged_refuses(submodule_factory, cli_runner) -> None:
    """Diverged history is refused with merge instructions."""
    worktree, sources = submodule_factory("pkg-a")
    commit_file(sources["pkg-a"], "PKGBUILD", "remote\n", "remote bump")
    sm_repo = worktree.submodules["pkg-a"].module()
    commit_file(sm_repo, "PKGBUILD", "local\n", "local bump")

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "pkg-a"])

    assert result.exit_code == 1
    assert "merge inside" in result.output.lower()
