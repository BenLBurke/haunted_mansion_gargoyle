#!/usr/bin/env python3
"""Regenerates pico-w/ota_manifest.json from the current pico-w/src/ tree.

Run this on a PC (not the device) before tagging each release, after
bumping the version in pico-w/src/version.json:

    python3 pico-w/scripts/generate_manifest.py

boot.py is deliberately excluded -- it's never touched by OTA updates (see
the comment at the top of boot.py for why). Everything else under
pico-w/src/ is included, including version.json itself, so the device's
recorded version updates automatically as part of applying the update.
"""

import json
import pathlib
import sys

SRC_DIR = pathlib.Path(__file__).resolve().parent.parent / "src"
MANIFEST_PATH = pathlib.Path(__file__).resolve().parent.parent / "ota_manifest.json"
EXCLUDE_NAMES = {"boot.py"}
EXCLUDE_DIR_NAMES = {"__pycache__"}


def collect_files():
    files = []
    for path in sorted(SRC_DIR.rglob("*")):
        if path.is_dir():
            continue
        if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
            continue
        relpath = path.relative_to(SRC_DIR).as_posix()
        if relpath in EXCLUDE_NAMES:
            continue
        files.append(relpath)
    return files


def read_version():
    version_path = SRC_DIR / "version.json"
    with version_path.open() as fh:
        return json.load(fh)["version"]


def main():
    version = read_version()
    files = collect_files()

    if "version.json" not in files:
        print("error: version.json missing from pico-w/src/ -- can't generate a manifest", file=sys.stderr)
        return 1

    manifest = {"version": version, "files": files}
    with MANIFEST_PATH.open("w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")

    print("wrote {} (version {}, {} files)".format(MANIFEST_PATH, version, len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
