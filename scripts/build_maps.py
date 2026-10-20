#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 CERN for the benefit of the SHiP Collaboration
#
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Convert the FairShip field maps listed in placements.json and install them.

Each map is fetched from FairShip at the pinned commit (or taken from a local
directory), checked against its sha256, converted with fairship_to_fieldmap
and written to <prefix>/share/field/ together with placements.json and
field_maps.libsonnet.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARE = REPO_ROOT / "share" / "field"
MANIFEST = SHARE / "placements.json"
JSONNET_LIB = SHARE / "field_maps.libsonnet"
DEFAULT_CACHE = Path(tempfile.gettempdir()) / "ship-field-maps"

# GitHub source archives contain only git-lfs pointer files for
# FairShip's maps; the media host serves the actual content.
MEDIA_URL = "https://media.githubusercontent.com/media/{repo}/{commit}/{path}"


def sha256sum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url, dest):
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as response, open(tmp, "wb") as out:
        shutil.copyfileobj(response, out)
    tmp.replace(dest)


def source_file(entry, fairship, input_dir, cache_dir):
    """Return a verified local copy of the FairShip map behind `entry`."""
    name = Path(entry["source"]).name
    if input_dir is not None:
        path = input_dir / name
    else:
        path = cache_dir / entry["sha256"] / name
        if not path.exists() or sha256sum(path) != entry["sha256"]:
            path.parent.mkdir(parents=True, exist_ok=True)
            repo = fairship["repository"].removeprefix("https://github.com/")
            url = MEDIA_URL.format(
                repo=repo, commit=fairship["commit"], path=entry["source"]
            )
            print(f"fetching {url}", flush=True)
            fetch(url, path)
    actual = sha256sum(path)
    if actual != entry["sha256"]:
        sys.exit(
            f"{path}: sha256 {actual} does not match {entry['sha256']} "
            "from placements.json"
        )
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True, help="install prefix")
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="directory with the FairShip map files (e.g. FairShip/files); "
        "skips the download",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE,
        help="where downloaded maps are kept (default: %(default)s)",
    )
    parser.add_argument(
        "--converter",
        default="fairship_to_fieldmap",
        help="fairship_to_fieldmap executable (default: from PATH)",
    )
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    fairship = manifest["fairship"]
    out_dir = args.prefix / "share" / "field"
    out_dir.mkdir(parents=True, exist_ok=True)

    for map_name, entry in manifest["maps"].items():
        src = source_file(entry, fairship, args.input_dir, args.cache_dir)
        # Record the FairShip file at its pinned commit, not the local copy,
        # which may be a cache or build directory.
        source = f"{fairship['repository']}/blob/{fairship['commit']}/{entry['source']}"
        cmd = [
            args.converter,
            "--name",
            map_name,
            "--symmetry",
            entry["symmetry"],
            "--source",
            source,
            "--comment",
            entry["comment"],
            str(src),
            str(out_dir / entry["file"]),
        ]
        print(" ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)

    shutil.copy2(MANIFEST, out_dir / MANIFEST.name)
    shutil.copy2(JSONNET_LIB, out_dir / JSONNET_LIB.name)


if __name__ == "__main__":
    main()
