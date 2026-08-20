"""Tests for the ``setup`` command."""

from __future__ import annotations

from pathlib import Path

HOOK_NAMES = ("pre-commit", "prepare-commit-msg")


def _hooks_dir(worktree) -> Path:
    return Path(worktree.submodules["pkg-a"].module().git_dir) / "hooks"


def test_setup_installs_hooks(submodule_factory, cli_runner) -> None:
    """Setup installs executable hooks into each submodule."""
    worktree, _ = submodule_factory("pkg-a")
    hooks = _hooks_dir(worktree)

    result = cli_runner(str(worktree.working_tree_dir), ["setup"])

    assert result.exit_code == 0
    for name in HOOK_NAMES:
        hook = hooks / name
        assert hook.is_file()
        assert hook.stat().st_mode & 0o111
        assert "aurmod" in hook.read_text(encoding="utf-8")


def test_setup_idempotent(submodule_factory, cli_runner) -> None:
    """Running setup twice is harmless."""
    worktree, _ = submodule_factory("pkg-a")
    cli_runner(str(worktree.working_tree_dir), ["setup"])

    result = cli_runner(str(worktree.working_tree_dir), ["setup"])

    assert result.exit_code == 0


def test_setup_keeps_existing_hooks(submodule_factory, cli_runner) -> None:
    """Existing non-aurmod hooks are not overwritten."""
    worktree, _ = submodule_factory("pkg-a")
    hooks = _hooks_dir(worktree)
    hooks.mkdir(parents=True, exist_ok=True)
    target = hooks / "pre-commit"
    target.write_text("#!/bin/sh\n# custom\n", encoding="utf-8")

    result = cli_runner(str(worktree.working_tree_dir), ["setup"])

    assert result.exit_code == 0
    assert "Skipping pre-commit" in result.output
    assert target.read_text(encoding="utf-8") == "#!/bin/sh\n# custom\n"
    assert (hooks / "prepare-commit-msg").is_file()


def test_setup_no_submodules(repo_factory, cli_runner) -> None:
    """Setup without submodules fails."""
    repo = repo_factory()

    result = cli_runner(str(repo.working_tree_dir), ["setup"])

    assert result.exit_code == 1
    assert "No submodules found to install hooks into." in result.output
