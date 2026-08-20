#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_arguments():
    parser = argparse.ArgumentParser(description="Build the Chrome extension ZIP")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
    )
    parser.add_argument(
        "--extension-dir",
        type=Path,
        default=PROJECT_ROOT / "extension",
        help="extension source directory",
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    extension_directory = arguments.extension_dir.expanduser().resolve()
    version = json.loads((extension_directory / "manifest.json").read_text())["version"]
    output = arguments.output or (
        PROJECT_ROOT / "dist" / f"chrome-url-router-extension-{version}.zip"
    )
    output = output.expanduser().resolve()
    output.parent.mkdir(mode=0o755, parents=True, exist_ok=True)

    files = sorted(path for path in extension_directory.rglob("*") if path.is_file())
    with ZipFile(output, "w") as archive:
        for path in files:
            relative_path = path.relative_to(extension_directory).as_posix()
            contents = path.read_bytes()
            if relative_path == "manifest.json":
                manifest = json.loads(contents)
                manifest.pop("key", None)
                contents = (json.dumps(manifest, indent=2) + "\n").encode()

            entry = ZipInfo(relative_path, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, contents)

    print(output)


if __name__ == "__main__":
    main()
