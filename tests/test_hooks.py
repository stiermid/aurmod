"""Tests for the bundled git-hook commands."""

from __future__ import annotations

from pathlib import Path

from git import Repo, Submodule
from helpers import commit_file


def _sm_dir(worktree) -> Path:
    return Path(worktree.submodules["pkg-a"].module().working_tree_dir)


def test_prepare_commit_msg_prefills(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """The message file is prefilled for a staged PKGBUILD."""
    worktree, _ = submodule_factory("pkg-a")
    sm_dir = _sm_dir(worktree)
    (sm_dir / "PKGBUILD").write_text(
        "pkgname=pkg-a\npkgver=2\npkgrel=1\n", encoding="utf-8"
    )
    (sm_dir / ".SRCINFO").write_text(
        "pkgbase = pkg-a\npkgver = 2\npkgrel = 1\n", encoding="utf-8"
    )
    worktree.submodules["pkg-a"].module().git.add("PKGBUILD", ".SRCINFO")
    msg = sm_dir / "COMMIT_EDITMSG"
    msg.write_text("placeholder\n", encoding="utf-8")
    monkeypatch.setattr("aurmod.checks.has_makepkg", lambda: False)

    result = cli_runner(str(sm_dir), ["prepare-commit-msg", str(msg)])

    assert result.exit_code == 0
    content = msg.read_text(encoding="utf-8")
    assert content.startswith("upgpkg: pkg-a 2-1")


def test_prepare_commit_msg_initial_upload(
    tmp_path, cli_runner, monkeypatch
) -> None:
    """A newly added PKGBUILD gets an initial-upload line."""
    worktree = Repo.init(tmp_path / "worktree")
    commit_file(worktree, "README.md", "root\n", "initial commit")
    source = Repo.init(tmp_path / "source-pkg-a")
    commit_file(source, ".gitignore", "*.pkg.tar*\n", "initial commit")
    Submodule.add(
        worktree,
        name="pkg-a",
        path="pkg-a",
        url=f"file://{source.working_tree_dir}",
    )
    worktree.git.add(".gitmodules")
    worktree.index.commit("add pkg-a")
    sm_repo = worktree.submodules["pkg-a"].module()
    sm_dir = Path(sm_repo.working_tree_dir)
    (sm_dir / "PKGBUILD").write_text(
        "pkgname=pkg-a\npkgver=1\npkgrel=1\n", encoding="utf-8"
    )
    (sm_dir / ".SRCINFO").write_text(
        "pkgbase = pkg-a\npkgver = 1\npkgrel = 1\n", encoding="utf-8"
    )
    sm_repo.git.add("PKGBUILD", ".SRCINFO")
    msg = sm_dir / "COMMIT_EDITMSG"
    msg.write_text("placeholder\n", encoding="utf-8")
    monkeypatch.setattr("aurmod.checks.has_makepkg", lambda: False)

    result = cli_runner(str(sm_dir), ["prepare-commit-msg", str(msg)])

    assert result.exit_code == 0
    assert msg.read_text(encoding="utf-8").startswith(
        "Initial upload: pkg-a 1-1"
    )


def test_pre_commit_passes_without_makepkg(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """Without makepkg the hook warns and passes."""
    worktree, _ = submodule_factory("pkg-a")
    sm_dir = _sm_dir(worktree)
    (sm_dir / "PKGBUILD").write_text(
        "pkgname=pkg-a\npkgver=2\n", encoding="utf-8"
    )
    worktree.submodules["pkg-a"].module().git.add("PKGBUILD")
    monkeypatch.setattr("aurmod.checks.has_makepkg", lambda: False)

    result = cli_runner(str(sm_dir), ["pre-commit"])

    assert result.exit_code == 0
    assert "makepkg not found" in result.output


def test_pre_commit_fails_on_bad_sources(
    submodule_factory, cli_runner, monkeypatch
) -> None:
    """The hook fails when source verification fails."""
    worktree, _ = submodule_factory("pkg-a")
    sm_dir = _sm_dir(worktree)
    (sm_dir / "PKGBUILD").write_text(
        "pkgname=pkg-a\npkgver=2\n", encoding="utf-8"
    )
    worktree.submodules["pkg-a"].module().git.add("PKGBUILD")

    class Ok:
        returncode = 0
        stdout = "pkgbase = pkg-a\npkgver = 2\npkgrel = 1\n"
        stderr = ""

    class Bad:
        returncode = 1
        stdout = ""
        stderr = "checksum mismatch"

    def fake_run(cmd, *args, **kwargs):
        if cmd[0] == "makepkg" and "--printsrcinfo" in cmd:
            return Ok()
        return Bad()

    monkeypatch.setattr("aurmod.checks.has_makepkg", lambda: True)
    monkeypatch.setattr("aurmod.checks.subprocess.run", fake_run)

    result = cli_runner(str(sm_dir), ["pre-commit"])

    assert result.exit_code == 1
    assert "Source verification failed" in result.output
