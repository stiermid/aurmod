"""Tests for the ``update`` command."""

from __future__ import annotations

from pathlib import Path

import aurmod.commands.update as update_mod
from aurmod.checks import IntegrityError


def _write_pkg(sm_dir: Path, version: str = "2") -> None:
    (sm_dir / "PKGBUILD").write_text(
        f"pkgname=pkg-a\npkgver={version}\npkgrel=1\n", encoding="utf-8"
    )
    (sm_dir / ".SRCINFO").write_text(
        f"pkgbase = pkg-a\npkgver = {version}\npkgrel = 1\n",
        encoding="utf-8",
    )


def test_update_commits_in_both_repos(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """Updating a dirty submodule commits in both repositories."""
    worktree, _ = submodule_factory("pkg-a")
    sm_dir = Path(worktree.submodules["pkg-a"].module().working_tree_dir)
    _write_pkg(sm_dir)
    monkeypatch.setattr("aurmod.checks.has_makepkg", lambda: False)

    result = cli_runner(str(worktree.working_tree_dir), ["update", "pkg-a"])

    assert result.exit_code == 0
    assert "makepkg not found" in result.output
    assert "upgpkg: pkg-a 2-1" in result.output
    sm_repo = worktree.submodules["pkg-a"].module()
    assert sm_repo.head.commit.message.strip() == "upgpkg: pkg-a 2-1"
    assert worktree.head.commit.message.strip() == "upgpkg: pkg-a 2-1"
    assert worktree.is_dirty() is False


def test_update_no_changes(submodule_factory, cli_runner) -> None:
    """Updating a clean submodule fails."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["update", "pkg-a"])

    assert result.exit_code == 1
    assert "No changes to commit for package pkg-a." in result.output


def test_update_integrity_failure(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """An integrity failure aborts without committing in either repo."""
    worktree, _ = submodule_factory("pkg-a")
    sm_dir = Path(worktree.submodules["pkg-a"].module().working_tree_dir)
    _write_pkg(sm_dir)

    def fail(*args, **kwargs):
        raise IntegrityError("Source verification failed")

    monkeypatch.setattr(update_mod, "verify_package", fail)

    before_worktree = worktree.head.commit.hexsha
    before_sm = worktree.submodules["pkg-a"].module().head.commit.hexsha

    result = cli_runner(str(worktree.working_tree_dir), ["update", "pkg-a"])

    assert result.exit_code == 1
    assert "Source verification failed" in result.output
    assert worktree.head.commit.hexsha == before_worktree
    assert worktree.submodules["pkg-a"].module().head.commit.hexsha == before_sm


def test_update_message_override(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """A custom message overrides the generated one."""
    worktree, _ = submodule_factory("pkg-a")
    sm_dir = Path(worktree.submodules["pkg-a"].module().working_tree_dir)
    _write_pkg(sm_dir)
    monkeypatch.setattr("aurmod.checks.has_makepkg", lambda: False)

    result = cli_runner(
        str(worktree.working_tree_dir), ["update", "pkg-a", "-m", "custom msg"]
    )

    assert result.exit_code == 0
    assert worktree.head.commit.message.strip() == "custom msg"


def test_update_unknown_package(submodule_factory, cli_runner) -> None:
    """Updating a package that is not tracked fails."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["update", "ghost"])

    assert result.exit_code == 1
    assert "Package ghost is not in repo." in result.output
