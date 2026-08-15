"""Shared fixtures for the aurmod test suite.

The fixtures create real git repositories in temporary directories so the
CLI and its helpers run against an actual git setup.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner
from git import Repo, Submodule
from helpers import commit_file, cwd_context

from aurmod.cli import cli

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from click.testing import Result

    RepoFactory = Callable[..., Repo]
    CliRunnerCallable = Callable[[str, list[str]], Result]


@pytest.fixture(scope="session", autouse=True)
def git_env(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Provide an isolated git configuration for spawned git processes.

    The user's global config may enable GPG signing, and modern git blocks
    local ``file://`` submodules by default. This fixture points git at a
    private config that disables signing, allows file submodules and sets a
    test identity.
    """
    config_dir = tmp_path_factory.mktemp("gitconfig")
    config = config_dir / "config"
    config.write_text(
        "\n".join(
            [
                "[user]",
                "\tname = AURMod Test",
                "\temail = aurmod@test.local",
                "[commit]",
                "\tgpgsign = false",
                '[protocol "file"]',
                "\tallow = always",
                "[safe]",
                "\tdirectory = *",
                "[init]",
                "\tdefaultbranch = master",
                "",
            ]
        ),
        encoding="utf-8",
    )
    old = os.environ.get("GIT_CONFIG_GLOBAL")
    os.environ["GIT_CONFIG_GLOBAL"] = str(config)
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("GIT_CONFIG_GLOBAL", None)
        else:
            os.environ["GIT_CONFIG_GLOBAL"] = old


@pytest.fixture
def repo_factory(tmp_path: Path) -> RepoFactory:
    """Return a callable creating an initialized repository with a commit."""

    def _factory(name: str = "repo") -> Repo:
        repo = Repo.init(tmp_path / name)
        commit_file(repo, "README.md", "initial\n", "initial commit")
        return repo

    return _factory


@pytest.fixture
def make_aur_remote(tmp_path: Path) -> Callable[[str], Path]:
    """Return a callable creating a fake AUR package repository.

    The returned base directory holds one repository per requested package,
    mimicking the layout used by the ``add`` command.
    """

    def _make(pkgname: str) -> Path:
        base = tmp_path / "aur"
        repo = Repo.init(base / pkgname)
        commit_file(repo, "PKGBUILD", f"pkgname={pkgname}\n", "initial commit")
        return base

    return _make


@pytest.fixture
def submodule_factory(
    tmp_path: Path,
) -> Callable[..., tuple[Repo, dict[str, Repo]]]:
    """Return a callable creating a worktree with one submodule per package.

    Each submodule points at a local source repository, so sync operations
    can be exercised without network access.
    """

    def _factory(*pkgnames: str) -> tuple[Repo, dict[str, Repo]]:
        worktree = Repo.init(tmp_path / "worktree")
        commit_file(worktree, "README.md", "root\n", "initial commit")
        sources: dict[str, Repo] = {}
        for pkgname in pkgnames:
            source = Repo.init(tmp_path / f"source-{pkgname}")
            commit_file(
                source, "PKGBUILD", f"pkgname={pkgname}\n", "initial commit"
            )
            Submodule.add(
                worktree,
                name=pkgname,
                path=pkgname,
                url=f"file://{source.working_tree_dir}",
            )
            sources[pkgname] = source
        worktree.git.add(".gitmodules")
        worktree.index.commit(f"add {', '.join(pkgnames)}")
        return worktree, sources

    return _factory


@pytest.fixture
def cli_runner() -> CliRunnerCallable:
    """Return a callable running the CLI inside a given working directory."""

    def _run(cwd: str, args: list[str]) -> Result:
        runner = CliRunner()
        with cwd_context(cwd):
            return runner.invoke(cli, args)

    return _run
