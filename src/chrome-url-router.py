#!/usr/bin/env python3

import json
import os
import select
import shutil
import socket
import stat
import struct
import sys
from pathlib import Path
from urllib.parse import urlsplit


MAX_MESSAGE_SIZE = 1024 * 1024
SOCKET_FILENAME = "chrome-url-router.sock"
RESPONSE_TIMEOUT = 5.0
BROWSER_ENVIRONMENT_VARIABLE = "CHROME_URL_ROUTER_BROWSER"
BROWSER_CANDIDATES = (
    "google-chrome-stable",
    "google-chrome",
    "chromium",
    "chromium-browser",
)


def get_socket_path():
    runtime_directory = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_directory is None:
        runtime_directory = f"/run/user/{os.getuid()}"
    return Path(runtime_directory) / SOCKET_FILENAME


def validate_url(value):
    if not isinstance(value, str):
        raise ValueError("URL must be a string")
    if len(value.encode()) > MAX_MESSAGE_SIZE:
        raise ValueError("URL is too long")

    parsed = urlsplit(value)
    if parsed.scheme not in {"file", "http", "https"}:
        raise ValueError("unsupported URL scheme")
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise ValueError("HTTP URL has no host")
    if parsed.scheme == "file" and not parsed.path:
        raise ValueError("file URL has no path")
    return value


def encode_socket_message(message):
    payload = json.dumps(message, separators=(",", ":")).encode() + b"\n"
    if len(payload) > MAX_MESSAGE_SIZE:
        raise ValueError("socket message is too large")
    return payload


def read_socket_message(connection):
    payload = bytearray()
    while not payload.endswith(b"\n"):
        chunk = connection.recv(4096)
        if not chunk:
            raise RuntimeError("socket connection closed")
        payload.extend(chunk)
        if len(payload) > MAX_MESSAGE_SIZE:
            raise ValueError("socket message is too large")
    return json.loads(payload)


def write_native_message(message):
    payload = json.dumps(message, separators=(",", ":")).encode()
    if len(payload) > MAX_MESSAGE_SIZE:
        raise ValueError("native message is too large")

    sys.stdout.buffer.write(struct.pack("=I", len(payload)))
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def read_exact(file_descriptor, size):
    payload = bytearray()
    while len(payload) < size:
        chunk = os.read(file_descriptor, size - len(payload))
        if not chunk:
            raise EOFError("native messaging connection closed")
        payload.extend(chunk)
    return bytes(payload)


def read_native_message(file_descriptor):
    readable, _, _ = select.select([file_descriptor], [], [], RESPONSE_TIMEOUT)
    if not readable:
        raise TimeoutError("Chrome extension did not respond")

    size = struct.unpack("=I", read_exact(file_descriptor, 4))[0]
    if size > MAX_MESSAGE_SIZE:
        raise ValueError("native message is too large")
    return json.loads(read_exact(file_descriptor, size))


def send_response(connection, message):
    try:
        connection.sendall(encode_socket_message(message))
    except OSError:
        pass


def handle_client(connection, native_input):
    try:
        request = read_socket_message(connection)
        url = validate_url(request.get("url"))
    except Exception as error:
        send_response(connection, {"error": str(error), "ok": False})
        return

    try:
        write_native_message({"url": url})
        response = read_native_message(native_input)
        if not isinstance(response, dict) or not isinstance(response.get("ok"), bool):
            raise ValueError("invalid response from Chrome extension")
    except Exception as error:
        send_response(connection, {"error": str(error), "ok": False})
        raise

    send_response(connection, response)


def remove_stale_socket(path):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return

    if not stat.S_ISSOCK(mode):
        raise RuntimeError(f"refusing to replace non-socket path: {path}")

    probe = socket.socket(socket.AF_UNIX)
    probe.settimeout(0.1)
    try:
        probe.connect(str(path))
    except (ConnectionRefusedError, FileNotFoundError):
        path.unlink(missing_ok=True)
    else:
        raise RuntimeError("another Chrome URL router is already running")
    finally:
        probe.close()


def run_native_host():
    socket_path = get_socket_path()
    socket_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    remove_stale_socket(socket_path)

    native_input = sys.stdin.fileno()
    with socket.socket(socket.AF_UNIX) as server:
        previous_umask = os.umask(0o177)
        try:
            server.bind(str(socket_path))
        finally:
            os.umask(previous_umask)

        server.listen()
        socket_inode = socket_path.stat().st_ino
        try:
            while True:
                readable, _, _ = select.select([native_input, server], [], [])
                if native_input in readable:
                    if os.read(native_input, 1) == b"":
                        return
                    raise RuntimeError("unexpected message from Chrome extension")

                connection, _ = server.accept()
                with connection:
                    connection.settimeout(RESPONSE_TIMEOUT)
                    handle_client(connection, native_input)
        finally:
            try:
                if socket_path.stat().st_ino == socket_inode:
                    socket_path.unlink()
            except FileNotFoundError:
                pass


def send_url(url):
    request = encode_socket_message({"url": validate_url(url)})
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(RESPONSE_TIMEOUT)
        connection.connect(str(get_socket_path()))
        connection.sendall(request)
        result = read_socket_message(connection)

    if result.get("ok") is not True:
        raise RuntimeError(result.get("error", "Chrome rejected the URL"))


def find_browser():
    configured_browser = os.environ.get(BROWSER_ENVIRONMENT_VARIABLE)
    candidates = (configured_browser,) if configured_browser else BROWSER_CANDIDATES

    for candidate in candidates:
        if os.path.sep in candidate:
            path = Path(candidate).expanduser()
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
        else:
            path = shutil.which(candidate)
            if path is not None:
                return path

    if configured_browser:
        raise RuntimeError(
            f"browser is not executable: {configured_browser}"
        )
    raise RuntimeError("Google Chrome or Chromium was not found")


def open_in_browser(arguments):
    browser = find_browser()
    os.execv(browser, [browser, *arguments])


def route_urls(arguments):
    if not arguments:
        open_in_browser([])

    try:
        urls = [validate_url(argument) for argument in arguments]
    except ValueError:
        open_in_browser(arguments)

    for index, url in enumerate(urls):
        try:
            send_url(url)
        except Exception:
            open_in_browser(arguments[index:])


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "send":
        if len(sys.argv) != 3:
            raise ValueError("usage: chrome-url-router send URL")
        send_url(sys.argv[2])
        return

    if len(sys.argv) >= 2 and sys.argv[1] == "open":
        route_urls(sys.argv[2:])
        return

    run_native_host()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"chrome-url-router: {error}", file=sys.stderr)
        raise SystemExit(1) from None
