// SPDX-FileCopyrightText: 2026 CERN for the benefit of the SHiP Collaboration
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//
// SHiP field maps and where they sit in the geometry, for jsonnet
// configurations. Add the directory holding this file to the import path
// (`-J $CONDA_PREFIX/share/field`) and use
//
//   local field_maps = import 'field_maps.libsonnet';
//   { cpp: 'field_map_provider', magnets: field_maps.magnets }
//
// Translations are in mm and only valid for `geometry.version` of
// the shipgeometry package.
local placements = import 'placements.json';

{
  geometry: placements.geometry,
  fairship: placements.fairship,
  maps: placements.maps,

  // One entry per magnet in the shape FieldMapSource expects:
  // {name, volume_pattern, file, map, translation}.
  magnets: [
    m { file: placements.maps[m.map].file }
    for m in placements.magnets
  ],
}
