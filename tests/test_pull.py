"""Tests for the ``pull`` command."""

from __future__ import annotations

from pathlib import Path

from helpers import commit_file


def test_pull_specific_package(submodule_factory, cli_runner) -> None:
    """Pulling a named package fast-forwards it and commits the pointer."""
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
    # pull commits the outer pointer, leaving a clean tree.
    assert worktree.head.commit.hexsha != before
    assert "Committed outer pointer" in result.output
    assert not worktree.is_dirty()
    assert worktree.git.diff("--cached", "--name-only").strip() == ""
    expected = sources["pkg-a"].head.commit.hexsha[:7]
    assert worktree.head.commit.message.strip() == f"pkg-a: {expected}"


def test_pull_unknown_package(submodule_factory, cli_runner) -> None:
    """Pulling a package that is not tracked fails."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "ghost"])

    assert result.exit_code == 1
    assert "Package ghost is not in repo." in result.output


def test_pull_specific_no_changes(submodule_factory, cli_runner) -> None:
    """Pulling an up-to-date package reports it without committing."""
    worktree, _ = submodule_factory("pkg-a")
    before = worktree.head.commit.hexsha

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "pkg-a"])

    assert result.exit_code == 0
    assert "already up to date" in result.output
    assert worktree.head.commit.hexsha == before


def test_pull_all_packages(submodule_factory, cli_runner) -> None:
    """Pulling everything updates all behind packages and commits."""
    worktree, sources = submodule_factory("pkg-a", "pkg-b")
    commit_file(sources["pkg-a"], "PKGBUILD", "pkgver=2\n", "bump a")
    commit_file(sources["pkg-b"], "PKGBUILD", "pkgver=3\n", "bump b")
    before = worktree.head.commit.hexsha

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "--all"])

    assert result.exit_code == 0
    for pkg in ("pkg-a", "pkg-b"):
        sm = worktree.submodules[pkg]
        assert str(sm.module().head.commit) == str(sources[pkg].head.commit)
    assert worktree.head.commit.hexsha != before
    assert "Committed outer pointer" in result.output
    assert not worktree.is_dirty()
    message = worktree.head.commit.message.strip()
    for pkg in ("pkg-a", "pkg-b"):
        expected = sources[pkg].head.commit.hexsha[:7]
        assert f"{pkg}: {expected}" in message


def test_pull_names_only_moved_packages(submodule_factory, cli_runner) -> None:
    """The outer commit message lists only packages that moved."""
    worktree, sources = submodule_factory("pkg-a", "pkg-b")
    commit_file(sources["pkg-b"], "PKGBUILD", "pkgver=9\n", "bump b")

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "--all"])

    assert result.exit_code == 0
    expected = sources["pkg-b"].head.commit.hexsha[:7]
    assert worktree.head.commit.message.strip() == f"pkg-b: {expected}"
    assert not worktree.is_dirty()


def test_pull_leaves_unrelated_staged_changes(
    submodule_factory, cli_runner
) -> None:
    """A pull commit contains only pulled pointers, nothing else."""
    worktree, sources = submodule_factory("pkg-a")
    commit_file(sources["pkg-a"], "PKGBUILD", "pkgver=2\n", "bump")
    notes = Path(str(worktree.working_tree_dir)) / "NOTES.txt"
    notes.write_text("my notes\n", encoding="utf-8")
    worktree.git.add("NOTES.txt")

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "--all"])

    assert result.exit_code == 0
    assert set(worktree.head.commit.stats.files) == {"pkg-a"}
    assert worktree.git.diff("--cached", "--name-only").strip() == "NOTES.txt"


def test_pull_preserves_push_staged_pointer(
    submodule_factory, cli_runner
) -> None:
    """An already-staged pointer is not committed by a no-op pull."""
    worktree, sources = submodule_factory("pkg-a")
    commit_file(sources["pkg-a"], "PKGBUILD", "pkgver=2\n", "bump")
    sm_repo = worktree.submodules["pkg-a"].module()
    sm_repo.git.fetch("origin")
    sm_repo.git.merge("--ff-only", "origin/master")
    before = worktree.head.commit.hexsha
    # Mimic `push` staging without `--commit`.
    worktree.git.add("pkg-a")
    assert worktree.git.diff("--cached", "--name-only").strip() == "pkg-a"

    result = cli_runner(str(worktree.working_tree_dir), ["pull", "pkg-a"])

    assert result.exit_code == 0
    assert "already up to date" in result.output
    assert worktree.head.commit.hexsha == before
    assert worktree.git.diff("--cached", "--name-only").strip() == "pkg-a"


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
