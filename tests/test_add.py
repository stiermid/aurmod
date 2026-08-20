"""Tests for the ``add`` command."""

from __future__ import annotations

from pathlib import Path

from git import IndexFile, Repo
from git.exc import GitCommandError
from helpers import commit_file

import aurmod.commands.add as add_mod


def _aur_url(base: Path) -> str:
    """Return an AUR_URL template pointing at a local fake AUR directory."""
    return f"file://{base}/{{pkgname}}"


def test_add_success(
    repo_factory, make_aur_remote, cli_runner, monkeypatch
) -> None:
    """Adding a package creates a committed submodule."""
    repo = repo_factory()
    base = make_aur_remote("pkg-a")
    monkeypatch.setattr(add_mod, "AUR_URL", _aur_url(base))

    result = cli_runner(str(repo.working_tree_dir), ["add", "pkg-a"])

    assert result.exit_code == 0
    assert "Successfully added: pkg-a" in result.output
    assert "pkg-a" in [sm.name for sm in repo.submodules]
    assert repo.head.commit.message.strip() == "addpkg: pkg-a"
    gitmodules = Path(repo.working_tree_dir) / ".gitmodules"
    assert "pkg-a" in gitmodules.read_text(encoding="utf-8")


def test_add_duplicate_package(
    repo_factory, make_aur_remote, cli_runner, monkeypatch
) -> None:
    """Adding a package that already exists is rejected."""
    repo = repo_factory()
    base = make_aur_remote("pkg-a")
    monkeypatch.setattr(add_mod, "AUR_URL", _aur_url(base))

    first = cli_runner(str(repo.working_tree_dir), ["add", "pkg-a"])
    assert first.exit_code == 0

    result = cli_runner(str(repo.working_tree_dir), ["add", "pkg-a"])
    assert result.exit_code == 1
    assert "Package pkg-a is already in repo." in result.output


def test_add_missing_package(
    repo_factory, cli_runner, monkeypatch, tmp_path
) -> None:
    """Adding a package that does not exist fails with a clear error."""
    repo = repo_factory()
    monkeypatch.setattr(add_mod, "AUR_URL", _aur_url(tmp_path / "aur"))

    result = cli_runner(str(repo.working_tree_dir), ["add", "ghost"])

    assert result.exit_code == 1
    assert "Adding submodule:" in result.output


def test_add_invalid_package_cleans_up(
    repo_factory, cli_runner, monkeypatch, tmp_path
) -> None:
    """A failed submodule add resets the index and removes untracked files."""
    repo = repo_factory()
    stray = Path(repo.working_tree_dir) / "stray.txt"
    stray.write_text("stray\n", encoding="utf-8")
    monkeypatch.setattr(add_mod, "AUR_URL", _aur_url(tmp_path / "aur"))

    def fake_add(*args, **kwargs):
        raise ValueError

    monkeypatch.setattr(add_mod.Submodule, "add", fake_add)

    result = cli_runner(str(repo.working_tree_dir), ["add", "ghost"])

    assert result.exit_code == 1
    assert "Make sure package ghost exists." in result.output
    assert not stray.exists()


def test_add_commit_failure(
    repo_factory, make_aur_remote, cli_runner, monkeypatch
) -> None:
    """A failing commit is reported as a ClickException."""
    repo = repo_factory()
    base = make_aur_remote("pkg-a")
    monkeypatch.setattr(add_mod, "AUR_URL", _aur_url(base))

    def failing_commit(self, message, **kwargs):
        raise GitCommandError("commit", 128)

    monkeypatch.setattr(IndexFile, "commit", failing_commit)

    result = cli_runner(str(repo.working_tree_dir), ["add", "pkg-a"])

    assert result.exit_code == 1
    assert "Committing changes:" in result.output


def test_add_not_a_git_repo(tmp_path, cli_runner) -> None:
    """Running add outside a git repository fails."""
    result = cli_runner(str(tmp_path), ["add", "pkg-a"])
    assert result.exit_code == 1
    assert "Git repo is not found." in result.output


def test_add_versioned_message(
    repo_factory, make_aur_remote, cli_runner, monkeypatch
) -> None:
    """Adding a package with .SRCINFO uses an initial-upload message."""
    repo = repo_factory()
    base = make_aur_remote("pkg-a")
    pkg_repo = Repo(base / "pkg-a")
    commit_file(
        pkg_repo,
        ".SRCINFO",
        "pkgbase = pkg-a\npkgver = 1.0\npkgrel = 1\n",
        "add srcinfo",
    )
    monkeypatch.setattr(add_mod, "AUR_URL", _aur_url(base))

    result = cli_runner(str(repo.working_tree_dir), ["add", "pkg-a"])

    assert result.exit_code == 0
    assert repo.head.commit.message.strip() == "Initial upload: pkg-a 1.0-1"
