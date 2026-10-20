<!--
SPDX-FileCopyrightText: 2026 CERN for the benefit of the SHiP Collaboration

SPDX-License-Identifier: LGPL-3.0-or-later
-->

# SHiP Field Maps

The SHiP magnetic field maps in the
[SHiP field-map format](https://github.com/ShipSoft/field_service/blob/main/docs/field_map_format.md),
plus a manifest that says where each map sits in the SHiP geometry. aegir and
Trout read the maps through
[field_service](https://github.com/ShipSoft/field_service). The conda package
is `ship-field-maps`.

## Contents

The package installs into `$PREFIX/share/field/`:

| File | Map | Magnet | Placement (mm) | Symmetry |
|---|---|---|---|---|
| `muon_shield_TRY_2026.root` | `muon_shield_TRY_2026` | `/SHiP/muon_shield` | (0, 0, 2040) | quadrant dipole |
| `spectrometer_V21_2455.root` | `spectrometer_V21_2455` | `/SHiP/magnet` | (0, 0, 89570) | none |
| `placements.json` | | | | |
| `field_maps.libsonnet` | | | | |

The muon shield map starts at the shield entrance. The spectrometer map is
centred on the magnet.

Both maps are converted with `fairship_to_fieldmap` from FairShip's `files/`
directory at the commit given in `placements.json`:

- `muon_shield_TRY_2026` comes from `TRY_2026.root`.
- `spectrometer_V21_2455` comes from
  `2026_07_02_MainSpectrometerField_V21_2455.root`.

The values are unchanged. Every other map in FairShip is outdated or was never
adopted, so none of them are included.

## Placements

The field-map format leaves placement to the consumer, so the translations
live in `placements.json`. They match the volume positions of the
`shipgeometry` version recorded in its `geometry` entry. Bump that version
together with the translations when the geometry moves.

FairShip uses its own geometry and places the maps differently: the shield at
about z = 2140 mm and the spectrometer at z = 89720 mm.

## Use

Bare filenames resolve under `$SHIPFIELD_ROOT/share/field/`. In a pixi or conda
environment, `SHIPFIELD_ROOT` is the environment prefix.

In jsonnet, add the directory to the import path (`-J $CONDA_PREFIX/share/field`)
and take the magnet list from the library:

```jsonnet
local field_maps = import 'field_maps.libsonnet';

{
  field: { cpp: 'field_map_provider', magnets: field_maps.magnets },
}
```

`field_maps.magnets` has one `{name, volume_pattern, file, map, translation}`
entry per magnet, which is the shape `SHiP::FieldMapSource` takes. Other code
can read `placements.json` directly.

## Build

```bash
pixi run build   # downloads the FairShip maps and converts them into build/
pixi run test    # compares the converted maps with the FairShip originals
pixi run install # installs into the pixi environment
```

`scripts/build_maps.py` downloads each map from FairShip at the pinned commit
and checks it against the sha256 in `placements.json`. Downloads are cached in
`$TMPDIR/ship-field-maps`. To use a local FairShip checkout instead, pass
`--input-dir path/to/FairShip/files`.

The test evaluates the converted maps at 2000 random grid nodes and compares
the result with FairShip's `Data` tree. For the muon shield it also checks the
three mirrored quadrants against the sign rules of FairShip's `ShipBFieldMap`.
It then checks that `field_maps.libsonnet` expands to the expected magnet
entries.

## Updating a map

1. Point `fairship.commit` in `share/field/placements.json` at the FairShip
   commit with the new file.
2. Update the map entry's `source` and `sha256`. The sha256 is the `oid` in the
   file's git-lfs pointer:
   `git show <commit>:files/<name>.root | grep oid`.
3. Run `pixi run test`.
