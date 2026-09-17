"""Tests for the ``add`` command."""

from __future__ import annotations

from pathlib import Path

from git import IndexFile
from git.exc import GitCommandError

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


def test_add_invalid_name(repo_factory, cli_runner) -> None:
    """Invalid AUR names are rejected before any network access."""
    repo = repo_factory()

    result = cli_runner(str(repo.working_tree_dir), ["add", "Bad Name"])

    assert result.exit_code == 1
    assert "Invalid package name" in result.output


def test_add_empty_offline(repo_factory, cli_runner, monkeypatch) -> None:
    """--empty creates a package folder without network access."""
    repo = repo_factory()
    monkeypatch.setattr(
        add_mod, "AUR_URL", "ssh://aur@aur.archlinux.org/{pkgname}.git"
    )
    # Force the template path even when makepkg is missing.
    import aurmod.pkg as pkg_mod

    monkeypatch.setattr(
        pkg_mod, "run_printsrcinfo", lambda _d: (None, "no makepkg")
    )

    result = cli_runner(
        str(repo.working_tree_dir), ["add", "--empty", "new-pkg"]
    )

    assert result.exit_code == 0
    assert "Successfully added: new-pkg" in result.output
    pkg_dir = Path(repo.working_tree_dir) / "new-pkg"
    assert (pkg_dir / "PKGBUILD").is_file()
    assert (pkg_dir / ".SRCINFO").is_file()
    sm = repo.submodules["new-pkg"]
    origin = sm.module().remotes.origin.url
    assert "aur.archlinux.org" in str(origin)
    assert repo.head.commit.message.strip() == "addpkg: new-pkg"
