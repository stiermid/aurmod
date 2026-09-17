"""Tests for the ``push`` command."""

from __future__ import annotations

from pathlib import Path

import aurmod.commands.push as push_mod


def _allow_push(source_repo) -> None:
    """Allow pushing into a non-bare test remote."""
    with source_repo.config_writer() as writer:
        writer.set_value("receive", "denyCurrentBranch", "ignore")


def test_push_success_stages_pointer(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """A clean package is pushed and the outer pointer is staged."""
    worktree, sources = submodule_factory("pkg-a")
    _allow_push(sources["pkg-a"])
    monkeypatch.setattr(push_mod, "srcinfo_status", lambda _d: ("ok", None))
    pkg_dir = Path(str(worktree.working_tree_dir)) / "pkg-a"
    (pkg_dir / ".SRCINFO").write_text(
        "pkgbase = pkg-a\n\tpkgver = 1.0\n\tpkgrel = 1\n\npkgname = pkg-a\n",
        encoding="utf-8",
    )
    sm_repo = worktree.submodules["pkg-a"].module()
    sm_repo.git.add(".SRCINFO")
    sm_repo.index.commit("add srcinfo")

    result = cli_runner(str(worktree.working_tree_dir), ["push", "pkg-a"])

    assert result.exit_code == 0
    assert "pushed" in result.output
    assert "Outer pointer staged" in result.output
    staged = worktree.git.diff("--cached", "--name-only")
    assert "pkg-a" in staged


def test_push_commit_records_version(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """--commit saves the outer pointer with a version message."""
    worktree, sources = submodule_factory("pkg-a")
    _allow_push(sources["pkg-a"])
    monkeypatch.setattr(push_mod, "srcinfo_status", lambda _d: ("ok", None))
    pkg_dir = Path(str(worktree.working_tree_dir)) / "pkg-a"
    (pkg_dir / ".SRCINFO").write_text(
        "pkgbase = pkg-a\n\tpkgver = 2.0\n\tpkgrel = 3\n\npkgname = pkg-a\n",
        encoding="utf-8",
    )
    sm_repo = worktree.submodules["pkg-a"].module()
    sm_repo.git.add(".SRCINFO")
    sm_repo.index.commit("add srcinfo")

    result = cli_runner(
        str(worktree.working_tree_dir), ["push", "pkg-a", "--commit"]
    )

    assert result.exit_code == 0
    assert worktree.head.commit.message.strip() == "pkg-a: 2.0-3"


def test_push_refuses_stale_srcinfo(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """Stale .SRCINFO blocks the push with the regenerate command."""
    worktree, _ = submodule_factory("pkg-a")
    monkeypatch.setattr(push_mod, "srcinfo_status", lambda _d: ("stale", None))
    pkg_dir = Path(str(worktree.working_tree_dir)) / "pkg-a"
    (pkg_dir / ".SRCINFO").write_text("pkgbase = pkg-a\n", encoding="utf-8")

    result = cli_runner(str(worktree.working_tree_dir), ["push", "pkg-a"])

    assert result.exit_code == 1
    assert "printsrcinfo" in result.output


def test_push_refuses_name_mismatch(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """Folder/pkgbase mismatch blocks the push with rename advice."""
    worktree, _ = submodule_factory("pkg-a")
    monkeypatch.setattr(push_mod, "srcinfo_status", lambda _d: ("ok", None))
    pkg_dir = Path(str(worktree.working_tree_dir)) / "pkg-a"
    (pkg_dir / ".SRCINFO").write_text("pkgbase = other\n", encoding="utf-8")

    result = cli_runner(str(worktree.working_tree_dir), ["push", "pkg-a"])

    assert result.exit_code == 1
    assert "rename" in result.output.lower()


def test_push_requires_package_or_all(submodule_factory, cli_runner) -> None:
    """Push without a target explains itself."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["push"])

    assert result.exit_code == 1
    assert "Specify a package or use --all" in result.output
