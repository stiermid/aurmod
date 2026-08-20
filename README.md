# aurmod

![PyPI - Version](https://img.shields.io/pypi/v/aurmod)
![PyPI - License](https://img.shields.io/pypi/l/aurmod)
![PyPI - Downloads](https://img.shields.io/pypi/dm/aurmod)
![Actions Status](https://github.com/stiermid/aurmod/actions/workflows/tests.yml/badge.svg)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)

**aurmod** is a tool for managing AUR packages with the help of git submodules.

## Usage

```sh
aurmod add <pkg>           # add a package as a submodule (commits "Initial upload: pkg 1.0-1")
aurmod update <pkg>        # verify a package, commit changes in the submodule and the worktree
aurmod sync [pkg]          # pull remote updates and record the new gitlinks
aurmod setup               # install git hooks into every submodule
```

### Committing package changes

`aurmod update <pkg>` runs a package integrity check, generates a commit
message from the package version (e.g. `upgpkg: pkg-a 2.0-1`), and commits
in both the submodule and the worktree. A custom message can be supplied
with `-m`.

The integrity check level is controlled by `git config aurmod.check`:

- `full` (default): whitespace check, `.SRCINFO` regeneration and
  `makepkg --verifysource`. Degrades to `light` with a warning when
  `makepkg` is not installed.
- `light`: whitespace and structural checks only.
- `off`: skip all checks.

### Git hooks

`aurmod setup` installs hooks into each submodule so that plain
`git commit` inside a package also validates it and prefills the commit
message:

- `prepare-commit-msg` fills in `upgpkg: pkg 1.0-1` / `Initial upload: ...`
- `pre-commit` regenerates `.SRCINFO` and verifies package sources
