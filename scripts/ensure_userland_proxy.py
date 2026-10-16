#!/usr/bin/env python3
"""Ensure /etc/docker/daemon.json has \"userland-proxy\": false.

Safe to run on the host before or after Compose. Merges JSON, backs up the
original when changing an existing file, and exits 0 when already correct.
Exit 10 means the file was changed and Docker should be restarted.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def ensure_daemon_userland_proxy(path: Path) -> tuple[bool, str]:
    data: dict = {}
    existed = path.is_file()
    if existed:
        raw = path.read_text(encoding="utf-8").strip()
        if raw:
            loaded = json.loads(raw)
            if not isinstance(loaded, dict):
                raise SystemExit(f"{path} must contain a JSON object")
            data = loaded
        if data.get("userland-proxy") is False:
            return False, f'{path} already has "userland-proxy": false'

    if existed:
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
        print(f"Backed up {path} to {backup}", flush=True)

    data["userland-proxy"] = False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if existed:
        return True, f'Set "userland-proxy": false in {path}'
    return True, f'Created {path} with "userland-proxy": false'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        default="/etc/docker/daemon.json",
        help="Path to Docker daemon.json (default: /etc/docker/daemon.json)",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Run systemctl restart docker when the file changed",
    )
    args = parser.parse_args(argv)
    changed, message = ensure_daemon_userland_proxy(Path(args.path))
    print(message, flush=True)
    if changed and args.restart:
        import subprocess

        print("Restarting Docker (systemctl restart docker)…", flush=True)
        subprocess.check_call(["systemctl", "restart", "docker"])
        print("Docker restarted. Recreate published containers with: docker compose up -d", flush=True)
    elif changed:
        print("Restart Docker, then recreate containers:", flush=True)
        print("  systemctl restart docker", flush=True)
        print("  docker compose up -d", flush=True)
        return 10
    return 0


if __name__ == "__main__":
    sys.exit(main())
