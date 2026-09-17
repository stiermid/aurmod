"""Shared git and submodule helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from git import InvalidGitRepositoryError
from git.exc import GitCommandError
from git.repo import Repo

if TYPE_CHECKING:
    from git import Submodule
    from git.types import PathLike


def is_submodule(repo: Repo) -> bool:
    """Check whether repo is submodule or not.

    A submodule has a ``.git`` gitfile whose gitdir lives under the
    parent repo's ``.git/modules/`` directory (linked worktrees live
    under ``.git/worktrees/`` instead).
    """
    expected_git_dir = os.path.join(str(repo.working_tree_dir), ".git")
    marker = os.path.join(".git", "modules")
    return os.path.isfile(expected_git_dir) and marker in str(repo.git_dir)


def get_root_repo(path: PathLike = ".") -> Repo:
    """Get the root git repository, stepping up if inside a submodule."""
    from click import ClickException

    try:
        repo = Repo(path)
    except InvalidGitRepositoryError:
        raise ClickException("Git repo is not found.")

    if not is_submodule(repo):
        return repo
    parent = Path(str(repo.working_tree_dir)).parent
    try:
        return Repo(str(parent))
    except InvalidGitRepositoryError:
        raise ClickException("Git repo is not found.")


def get_submodule(repo: Repo, name: str) -> Submodule:
    """Return the submodule ``name`` or raise a user-friendly error."""
    from click import ClickException

    try:
        return repo.submodules[name]
    except IndexError:
        raise ClickException(f"Package {name} is not in repo.")


def sorted_submodules(repo: Repo) -> list[Submodule]:
    """Return submodules sorted by name."""
    return sorted(repo.submodules, key=lambda sm: sm.name)


def require_submodules(repo: Repo) -> list[Submodule]:
    """Return sorted submodules or raise if the collection is empty."""
    from click import ClickException

    sms = sorted_submodules(repo)
    if not sms:
        raise ClickException("No packages in repo.")
    return sms


def submodule_head(sm: Submodule) -> str | None:
    """Return the checked-out commit of a submodule, if available."""
    try:
        if not sm.module_exists():
            return None
        return str(sm.module().head.commit.hexsha)
    except ValueError, GitCommandError:
        return None


def pointer_state(repo: Repo, sm: Submodule) -> dict[str, str | None]:
    """Compare folder HEAD against staged and committed outer pointers."""
    head = submodule_head(sm)
    try:
        committed = repo.git.rev_parse(f"HEAD:{sm.path}").strip()
    except GitCommandError:
        committed = None
    try:
        staged = repo.git.rev_parse(f":{sm.path}").strip()
    except GitCommandError:
        staged = committed
    if staged == "":
        staged = None
    state = "ok"
    if head is None or committed is None:
        state = "unknown"
    elif head != committed and staged == committed:
        state = "outdated"
    elif staged != committed and head == staged:
        state = "staged"
    elif head != staged or head != committed:
        state = "outdated"
    return {
        "head": head,
        "staged": staged,
        "committed": committed,
        "state": state,
    }


def current_branch(sm_repo: Repo) -> str | None:
    """Return the current branch name, or ``None`` when detached."""
    try:
        if sm_repo.head.is_detached:
            return None
        branch = sm_repo.active_branch
        return str(branch.name)
    except ValueError, TypeError:
        return None


def fetch_origin(sm_repo: Repo) -> bool:
    """Fetch ``origin`` quietly; return ``False`` on failure."""
    try:
        sm_repo.remotes.origin.fetch(prune=False)
    except AttributeError, GitCommandError, ValueError:
        return False
    return True


def ahead_behind(sm_repo: Repo) -> tuple[int | None, int | None]:
    """Return ``(ahead, behind)`` vs ``origin/master``.

    ``ahead`` counts local-only commits, ``behind`` counts remote-only
    commits. ``(None, None)`` means the upstream is missing.
    """
    try:
        sm_repo.git.rev_parse("--verify", "origin/master")
    except GitCommandError:
        return None, None
    try:
        ahead = int(
            sm_repo.git.rev_list("--count", "origin/master..HEAD").strip()
        )
        behind = int(
            sm_repo.git.rev_list("--count", "HEAD..origin/master").strip()
        )
    except GitCommandError, ValueError:
        return None, None
    return ahead, behind


def is_ancestor(sm_repo: Repo, maybe_ancestor: str, descendant: str) -> bool:
    """Check ``merge-base --is-ancestor`` without raising on failure."""
    try:
        sm_repo.git.execute(
            ["git", "merge-base", "--is-ancestor", maybe_ancestor, descendant]
        )
    except GitCommandError:
        return False
    return True


def whitespace_issues(sm_repo: Repo) -> str:
    """Return ``git diff --check`` output for worktree and index."""
    issues: list[str] = []
    for args in (["diff", "--check"], ["diff", "--cached", "--check"]):
        try:
            out = sm_repo.git.execute(["git", *args])
        except GitCommandError as exc:
            # git diff --check exits 2 when issues are found and
            # prints them to stdout.
            out = str(exc.stdout or "") if hasattr(exc, "stdout") else ""
        out = (out or "").strip()
        if out:
            issues.append(out)
    return "\n".join(issues)
