"""Console launcher for ADK Web using the repo's wrapped agents."""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
MAX_PORT_SCAN = 50


def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex((host, port)) != 0


def _pick_port(host: str, requested_port: int | None) -> tuple[int, bool]:
    if requested_port is not None:
        return requested_port, False

    base_port = int(os.getenv("ADK_WEB_PORT", str(DEFAULT_PORT)))
    for candidate in range(base_port, base_port + MAX_PORT_SCAN):
        if _is_port_available(host, candidate):
            return candidate, candidate != base_port

    raise RuntimeError(
        f"Could not find a free port in range {base_port}-{base_port + MAX_PORT_SCAN - 1}."
    )


def main() -> int:
    """Launch `adk web` against the wrapped agents directory."""
    parser = argparse.ArgumentParser(
        description="Launch ADK Web for this repository's agents.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=None)
    args, passthrough = parser.parse_known_args()

    port, auto_switched = _pick_port(args.host, args.port)
    if auto_switched:
        print(f"[i] Port 8000 is busy. Using port {port} instead.")

    adk_path = shutil.which("adk")
    if not adk_path:
        print("[!] Could not find the `adk` executable in the current environment.")
        return 1

    command = [
        adk_path,
        "web",
        str(AGENTS_DIR),
        "--host",
        args.host,
        "--port",
        str(port),
        *passthrough,
    ]
    return subprocess.call(command)


if __name__ == "__main__":
    sys.exit(main())
