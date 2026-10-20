<!--
SPDX-FileCopyrightText: 2026 CERN for the benefit of the SHiP Collaboration

SPDX-License-Identifier: LGPL-3.0-or-later
-->

# Contributing to SHiP Field Maps

## Development workflow

1. **Environment**: use [pixi](https://pixi.sh). `pixi run test` converts the
   maps and checks them against the FairShip originals.
2. **Pre-commit hooks**: [`prek`](https://github.com/j178/prek) runs the style
   and licensing checks. The tools come from the pixi `lint` environment.
   Install the hooks once with `pixi run install-hooks`, and run them on all
   files with `pixi run lint`.
3. **Branching**: work on a feature branch.
4. **Style**: Python is formatted and linted with `ruff`. Every new file needs
   an SPDX header, which `reuse lint` checks. `placements.json` can't carry
   one, so `REUSE.toml` covers it.
5. **Commits**: follow [Conventional Commits](https://www.conventionalcommits.org/).
   The allowed types are listed in `committed.toml`.
6. **Changing a map or a placement**: see "Updating a map" in the README. A
   change to a translation also needs a new `geometry.version`.
7. **Submission**: open a pull request against `main`. The `Pixi Build` CI
   check must pass.

## Licensing

This project is licensed under **LGPL-3.0-or-later**, the same licence as the
FairShip files the maps are converted from.
