# aurmod

![PyPI - Version](https://img.shields.io/pypi/v/aurmod)
![PyPI - License](https://img.shields.io/pypi/l/aurmod)
![PyPI - Downloads](https://img.shields.io/pypi/dm/aurmod)
![Actions Status](https://github.com/stiermid/aurmod/actions/workflows/tests.yml/badge.svg)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)

**aurmod** is a tool for managing AUR packages with the help of git submodules.

One folder holds all the AUR packages you maintain. Each package
folder is a complete AUR repository. The outer folder only remembers
which version of each package you last published.

## Commands

- `aurmod init` — set submodule behavior, install guards, check SSH.
- `aurmod add <name>` — clone an AUR repo as a new submodule.
- `aurmod add --empty <name>` — create a new package offline.
- `aurmod push <name> | --all [--commit]` — push to the AUR, then
  stage the new outer pointer.
- `aurmod pull <name> | --all` — fast-forward package folders
  from the AUR, then commit the new outer pointer.
- `aurmod status` — one line per package: version, dirtiness,
  SRCINFO state, ahead/behind, pointer state.
- `aurmod check <name> | --all` — report publish blockers.
- `aurmod log <name>` — history of one package.
- `aurmod exec --all -- <command>` — run a command in every package.

Publishing is always two steps: push the package folder, then save
the pointer in the outer folder. `push` stages the pointer for you;
use `--commit` to commit it at once as `foo: 1.0-2`. `pull` commits
the pointer automatically, since it only records upstream state.

Folder names must match `pkgbase` from `.SRCINFO`, and `.SRCINFO`
must match `makepkg --printsrcinfo > .SRCINFO` output.
