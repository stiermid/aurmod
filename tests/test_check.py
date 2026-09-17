"""Tests for the ``check`` command."""

from __future__ import annotations

from pathlib import Path

import aurmod.commands.check as check_mod


def test_check_ok(submodule_factory, cli_runner, monkeypatch) -> None:
    """A clean package reports OK."""
    worktree, _ = submodule_factory("pkg-a")
    monkeypatch.setattr(check_mod, "srcinfo_status", lambda _d: ("ok", None))
    monkeypatch.setattr(check_mod.shutil, "which", lambda _t: None)
    pkg_dir = Path(str(worktree.working_tree_dir)) / "pkg-a"
    (pkg_dir / "PKGBUILD").write_text("true\n", encoding="utf-8")
    (pkg_dir / ".SRCINFO").write_text("pkgbase = pkg-a\n", encoding="utf-8")

    result = cli_runner(str(worktree.working_tree_dir), ["check", "pkg-a"])

    assert result.exit_code == 0
    assert "pkg-a: OK" in result.output


def test_check_missing_files(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """Missing PKGBUILD/.SRCINFO are reported in plain language."""
    worktree, _ = submodule_factory("pkg-a")
    monkeypatch.setattr(check_mod.shutil, "which", lambda _t: None)
    pkg_dir = Path(str(worktree.working_tree_dir)) / "pkg-a"
    for name in ("PKGBUILD", ".SRCINFO"):
        target = pkg_dir / name
        if target.exists():
            target.unlink()

    result = cli_runner(str(worktree.working_tree_dir), ["check", "pkg-a"])

    assert result.exit_code == 1
    assert "missing PKGBUILD" in result.output
    assert "missing .SRCINFO" in result.output


def test_check_name_mismatch(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """A pkgbase mismatch tells the user to rename."""
    worktree, _ = submodule_factory("pkg-a")
    monkeypatch.setattr(check_mod, "srcinfo_status", lambda _d: ("ok", None))
    monkeypatch.setattr(check_mod.shutil, "which", lambda _t: None)
    pkg_dir = Path(str(worktree.working_tree_dir)) / "pkg-a"
    (pkg_dir / "PKGBUILD").write_text("true\n", encoding="utf-8")
    (pkg_dir / ".SRCINFO").write_text("pkgbase = other\n", encoding="utf-8")

    result = cli_runner(str(worktree.working_tree_dir), ["check", "pkg-a"])

    assert result.exit_code == 1
    assert "rename" in result.output.lower()


def test_check_requires_target(submodule_factory, cli_runner) -> None:
    """Check without a target explains itself."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["check"])

    assert result.exit_code == 1
    assert "Specify a package or use --all" in result.output
