"""Tests for the ``status`` command."""

from __future__ import annotations

from pathlib import Path


def test_status_reports_each_package(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """Status prints one line per package with sync state."""
    import aurmod.commands.status as status_mod

    worktree, _ = submodule_factory("pkg-a", "pkg-b")
    monkeypatch.setattr(status_mod, "srcinfo_status", lambda _d: ("ok", None))
    for name in ("pkg-a", "pkg-b"):
        pkg_dir = Path(str(worktree.working_tree_dir)) / name
        (pkg_dir / ".SRCINFO").write_text(
            f"pkgbase = {name}\n\tpkgver = 1.0\n\tpkgrel = 1\n\n"
            f"pkgname = {name}\n",
            encoding="utf-8",
        )

    result = cli_runner(str(worktree.working_tree_dir), ["status"])

    assert result.exit_code == 0
    for name in ("pkg-a", "pkg-b"):
        assert name in result.output
        assert "1.0-1" in result.output
    assert "pointer-ok" in result.output


def test_status_empty_collection(repo_factory, cli_runner) -> None:
    """Status with no packages explains itself."""
    repo = repo_factory()

    result = cli_runner(str(repo.working_tree_dir), ["status"])

    assert result.exit_code == 1
    assert "No packages" in result.output
