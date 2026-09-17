"""Tests for the ``init`` command."""

from __future__ import annotations

from pathlib import Path

import aurmod.commands.init as init_mod


def test_init_sets_configs_and_hooks(
    repo_factory, cli_runner, monkeypatch
) -> None:
    """Init writes submodule settings, hooks and reports SSH state."""
    repo = repo_factory()
    monkeypatch.setattr(init_mod, "_check_ssh", lambda: True)

    result = cli_runner(str(repo.working_tree_dir), ["init"])

    assert result.exit_code == 0
    assert "Configured" in result.output
    reader = repo.config_reader()
    assert reader.get_value("submodule", "recurse") in (True, "true")
    assert reader.get_value("push", "recurseSubmodules") == "check"
    hooks = Path(str(repo.working_tree_dir)) / ".git" / "hooks"
    assert (hooks / "pre-commit").is_file()
    assert (hooks / "pre-push").is_file()


def test_init_ssh_failure_prints_snippet(
    repo_factory, cli_runner, monkeypatch
) -> None:
    """When SSH fails, a ready-to-paste snippet is shown."""
    repo = repo_factory()
    monkeypatch.setattr(init_mod, "_check_ssh", lambda: False)

    result = cli_runner(str(repo.working_tree_dir), ["init"])

    assert result.exit_code == 0
    assert "Host aur.archlinux.org" in result.output
