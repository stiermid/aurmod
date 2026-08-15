"""Helper utilities for the test suite."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from git import Repo


def commit_file(repo: Repo, name: str, content: str, message: str) -> None:
    """Write a file to the repository and commit it.

    Args:
        repo: repository to modify.
        name: path of the file, relative to the working tree.
        content: file content.
        message: commit message.

    """
    path = Path(repo.working_tree_dir) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    repo.git.add(name)
    repo.index.commit(message)


@contextmanager
def cwd_context(path: str) -> Iterator[None]:
    """Temporarily change the current working directory.

    Args:
        path: directory to switch to.

    """
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)
