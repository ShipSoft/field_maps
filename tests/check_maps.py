#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 CERN for the benefit of the SHiP Collaboration
#
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Check the converted maps against the FairShip files they came from.

For a random sample of grid nodes of every map, the field that fieldmap_dump
evaluates from the converted file has to match the value stored in FairShip's
Data tree. For maps with quadrant symmetry the same nodes are also evaluated
in the other three quadrants, where FairShip's ShipBFieldMap flips Bx for
x < 0 and Bx, Bz for y < 0. Finally the jsonnet library has to expand to one
FieldMapSource entry per magnet whose file and map exist.
"""

import argparse
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import ROOT

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_maps

# FairShip stores floats in T; allow for float rounding and the converter's
# float storage.
ABS_TOL = 1e-5
REL_TOL = 1e-5
SAMPLES = 2000

# Sign of (Bx, By, Bz) when reflecting into (x<0, y<0).
QUADRANT_SIGNS = {
    (False, False): (1, 1, 1),
    (True, False): (-1, 1, 1),
    (False, True): (-1, 1, -1),
    (True, True): (1, 1, -1),
}


def read_fairship(path, rng):
    """Return (axes, samples): node axes in mm and sampled (i, j, k, B)."""
    f = ROOT.TFile.Open(str(path))
    rng_tree = f.Get("Range")
    rng_tree.GetEntry(0)
    axes = []
    for a in "xyz":
        lo = getattr(rng_tree, f"{a}Min")
        hi = getattr(rng_tree, f"{a}Max")
        step = getattr(rng_tree, f"d{a}")
        n = round((hi - lo) / step) + 1
        axes.append((lo * 10.0, step * 10.0, n))
    nx, ny, nz = (a[2] for a in axes)

    data = f.Get("Data")
    if data.GetEntries() != nx * ny * nz:
        sys.exit(f"{path}: {data.GetEntries()} entries, expected {nx * ny * nz}")
    data.SetBranchStatus("*", 0)
    for b in ("Bx", "By", "Bz"):
        data.SetBranchStatus(b, 1)

    samples = []
    for idx in sorted(rng.sample(range(nx * ny * nz), SAMPLES)):
        data.GetEntry(idx)
        i, rem = divmod(idx, ny * nz)
        j, k = divmod(rem, nz)
        samples.append((i, j, k, (data.Bx, data.By, data.Bz)))
    f.Close()
    return axes, samples


def evaluate(dump, path, map_name, points):
    stdin = "".join(f"{x!r} {y!r} {z!r}\n" for x, y, z in points)
    out = subprocess.run(
        [dump, str(path), map_name],
        input=stdin,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [tuple(map(float, line.split()[3:])) for line in out.splitlines()]


def close(a, b):
    return abs(a - b) <= ABS_TOL + REL_TOL * abs(b)


def check_map(name, entry, field_dir, src, dump, rng):
    axes, samples = read_fairship(src, rng)
    out_file = field_dir / entry["file"]

    quadrants = [(False, False)]
    if entry["symmetry"] == "quadrant_dipole":
        quadrants = list(QUADRANT_SIGNS)

    failures = 0
    for flip_x, flip_y in quadrants:
        points, expected = [], []
        signs = QUADRANT_SIGNS[(flip_x, flip_y)]
        for i, j, k, b in samples:
            x = axes[0][0] + i * axes[0][1]
            y = axes[1][0] + j * axes[1][1]
            z = axes[2][0] + k * axes[2][1]
            # A node on a mirror plane has no unique image; skip it there.
            if (flip_x and x == 0.0) or (flip_y and y == 0.0):
                continue
            points.append((-x if flip_x else x, -y if flip_y else y, z))
            expected.append(tuple(s * v for s, v in zip(signs, b)))
        got = evaluate(dump, out_file, name, points)
        for p, e, g in zip(points, expected, got):
            if not all(close(gv, ev) for gv, ev in zip(g, e)):
                failures += 1
                if failures <= 10:
                    print(f"  {name} at {p}: got {g}, FairShip {e}")
        print(
            f"{name}: quadrant x{'<' if flip_x else '>='}0 "
            f"y{'<' if flip_y else '>='}0, {len(points)} nodes checked"
        )
    return failures


def check_jsonnet(field_dir, manifest):
    jsonnet = shutil.which("jsonnet")
    if jsonnet is None:
        sys.exit("jsonnet not found")
    out = subprocess.run(
        [
            jsonnet,
            "-J",
            str(field_dir),
            "-e",
            "(import 'field_maps.libsonnet').magnets",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    magnets = json.loads(out)
    failures = 0
    if len(magnets) != len(manifest["magnets"]):
        print(f"jsonnet: {len(magnets)} magnets, expected {len(manifest['magnets'])}")
        failures += 1
    for m in magnets:
        if set(m) != {"name", "volume_pattern", "file", "map", "translation"}:
            print(f"jsonnet: unexpected keys in {m}")
            failures += 1
        if not (field_dir / m["file"]).is_file():
            print(f"jsonnet: {m['name']} refers to missing {m['file']}")
            failures += 1
        print(f"{m['name']}: {m['file']}:{m['map']} at {m['translation']} mm")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=build_maps.DEFAULT_CACHE,
    )
    parser.add_argument("--dump", default="fieldmap_dump")
    parser.add_argument("--seed", type=int, default=46)
    args = parser.parse_args()

    ROOT.gROOT.SetBatch(True)
    rng = random.Random(args.seed)
    field_dir = args.prefix / "share" / "field"
    manifest = json.loads((field_dir / "placements.json").read_text())

    failures = 0
    for name, entry in manifest["maps"].items():
        src = build_maps.source_file(
            entry, manifest["fairship"], args.input_dir, args.cache_dir
        )
        failures += check_map(name, entry, field_dir, src, args.dump, rng)
    failures += check_jsonnet(field_dir, manifest)

    if failures:
        sys.exit(f"{failures} check(s) failed")
    print("all checks passed")


if __name__ == "__main__":
    main()
