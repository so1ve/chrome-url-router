#!/usr/bin/env python3

import argparse
import json
import os
import shutil
from pathlib import Path


HOST_NAME = "dev.so1ve.chrome_url_router"
EXTENSION_ID = "kikebbdlmkhepgmdakiniblgpkpbaolh"
BROWSER_CONFIG_DIRECTORIES = {
    "chrome": "google-chrome",
    "chromium": "chromium",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOST_SOURCE = PROJECT_ROOT / "src" / "chrome-url-router.py"


def environment_path(name, fallback):
    value = os.environ.get(name)
    return Path(value).expanduser() if value else fallback


def desktop_quote(value):
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("`", "\\`")
        .replace("$", "\\$")
    )
    return f'"{escaped}"'


def write_text(path, content, mode=0o644):
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(mode)


def selected_manifest_directories(arguments, config_home):
    browsers = arguments.browsers
    if browsers is None:
        browsers = (
            list(BROWSER_CONFIG_DIRECTORIES)
            if arguments.action == "uninstall"
            else ["chrome"]
        )

    directories = [
        config_home
        / BROWSER_CONFIG_DIRECTORIES[browser]
        / "NativeMessagingHosts"
        for browser in browsers
    ]
    directories.extend(path.expanduser().resolve() for path in arguments.manifest_dirs)
    return list(dict.fromkeys(directories))


def install(arguments, executable, desktop_entry, manifest_directories):
    executable.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    shutil.copyfile(HOST_SOURCE, executable)
    executable.chmod(0o755)

    manifest = json.dumps(
        {
            "name": HOST_NAME,
            "description": "Routes external URLs to an existing normal Chrome window",
            "path": str(executable),
            "type": "stdio",
            "allowed_origins": [
                f"chrome-extension://{arguments.extension_id}/"
            ],
        },
        indent=2,
    )
    for directory in manifest_directories:
        write_text(directory / f"{HOST_NAME}.json", manifest + "\n")

    desktop = f"""[Desktop Entry]
Type=Application
Name=Chrome URL Router
Comment=Open links in the last focused normal Chrome window
Exec={desktop_quote(str(executable))} open %U
Icon=google-chrome
NoDisplay=true
Terminal=false
MimeType=application/xhtml+xml;text/html;x-scheme-handler/http;x-scheme-handler/https;
"""
    write_text(desktop_entry, desktop)

    print(f"Installed native host: {executable}")
    for directory in manifest_directories:
        print(f"Installed Chrome manifest: {directory / f'{HOST_NAME}.json'}")
    print(f"Installed desktop entry: {desktop_entry}")


def uninstall(executable, desktop_entry, manifest_directories):
    paths = [
        executable,
        desktop_entry,
        *(directory / f"{HOST_NAME}.json" for directory in manifest_directories),
    ]
    for path in paths:
        path.unlink(missing_ok=True)
        print(f"Removed: {path}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Install Chrome URL Router for the current Linux user"
    )
    parser.add_argument(
        "action",
        choices=("install", "uninstall"),
        default="install",
        nargs="?",
    )
    parser.add_argument(
        "--prefix",
        type=Path,
        help="installation prefix (default: ~/.local)",
    )
    parser.add_argument(
        "--browser",
        action="append",
        choices=tuple(BROWSER_CONFIG_DIRECTORIES),
        dest="browsers",
        help="browser whose Native Messaging directory should be configured",
    )
    parser.add_argument(
        "--manifest-dir",
        action="append",
        default=[],
        type=Path,
        dest="manifest_dirs",
        help="additional NativeMessagingHosts directory",
    )
    parser.add_argument(
        "--extension-id",
        default=EXTENSION_ID,
        help="extension ID allowed to connect to the native host",
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    home = Path.home()
    prefix = (arguments.prefix or home / ".local").expanduser().resolve()
    config_home = environment_path("XDG_CONFIG_HOME", home / ".config")
    data_home = environment_path("XDG_DATA_HOME", home / ".local" / "share")
    executable = prefix / "bin" / "chrome-url-router"
    desktop_entry = data_home / "applications" / "chrome-url-router.desktop"
    manifest_directories = selected_manifest_directories(arguments, config_home)

    if arguments.action == "install":
        install(arguments, executable, desktop_entry, manifest_directories)
    else:
        uninstall(executable, desktop_entry, manifest_directories)


if __name__ == "__main__":
    main()
