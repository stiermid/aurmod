"""Tests for the ``log`` and ``exec`` commands."""

from __future__ import annotations


def test_log_shows_package_history(submodule_factory, cli_runner) -> None:
    """Log shows history from inside the package folder."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["log", "pkg-a"])

    assert result.exit_code == 0
    assert "initial commit" in result.output


def test_log_unknown_package(submodule_factory, cli_runner) -> None:
    """Log of an unknown package fails clearly."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["log", "ghost"])

    assert result.exit_code == 1
    assert "not in repo" in result.output


def test_exec_single_package(submodule_factory, cli_runner, tmp_path) -> None:
    """Exec runs a command inside one package folder."""
    worktree, _ = submodule_factory("pkg-a")
    marker = tmp_path / "marker"

    result = cli_runner(
        str(worktree.working_tree_dir),
        ["exec", "pkg-a", "--", "touch", str(marker)],
    )

    assert result.exit_code == 0
    assert marker.exists()


def test_exec_all_packages(submodule_factory, cli_runner, tmp_path) -> None:
    """Exec --all runs in every package folder."""
    worktree, _ = submodule_factory("pkg-a", "pkg-b")

    result = cli_runner(
        str(worktree.working_tree_dir),
        ["exec", "--all", "--", "touch", "ran-all"],
    )

    assert result.exit_code == 0
    import os

    root = str(worktree.working_tree_dir)
    assert os.path.exists(os.path.join(root, "pkg-a", "ran-all"))
    assert os.path.exists(os.path.join(root, "pkg-b", "ran-all"))


def test_exec_requires_command(submodule_factory, cli_runner) -> None:
    """Exec without a command explains itself."""
    worktree, _ = submodule_factory("pkg-a")

    result = cli_runner(str(worktree.working_tree_dir), ["exec", "--all"])

    assert result.exit_code == 1
    assert "No command" in result.output
