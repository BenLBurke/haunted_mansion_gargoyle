#!/usr/bin/env python3
"""Standalone OTA updater/health-checker for the Pi Zero gargoyle.

Deliberately independent of the app's own venv and dependencies (stdlib
only) and run by its own systemd timer -- NOT from inside the running
gargoyle process. The update needs to restart that process and then watch
whether it comes back up healthy, and a process can't reliably do that to
itself: `systemctl restart` kills it before it could ever check the result.

Usage: python3 ota_apply.py [--config /etc/gargoyle/config.yaml]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request

REPO_DIR = "/opt/gargoyle"
SERVICE_NAME = "gargoyle.service"
HEALTH_CHECK_DELAY_SECONDS = 15
HEALTH_CHECK_RETRIES = 3


def _read_config_value(config_path: str, key: str, default: str) -> str:
    # Deliberately crude single-line scalar reader instead of importing
    # PyYAML -- this script needs to run even if the app's venv/dependencies
    # are broken, which is exactly the scenario it exists to recover from.
    try:
        with open(config_path) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("{}:".format(key)):
                    return line.split(":", 1)[1].strip().strip("'\"")
    except OSError:
        pass
    return default


def _run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def current_tag() -> str | None:
    result = _run(["git", "-C", REPO_DIR, "describe", "--tags", "--exact-match"])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def latest_release_tag(repo: str) -> str:
    url = "https://api.github.com/repos/{}/releases/latest".format(repo)
    req = urllib.request.Request(url, headers={"User-Agent": "gargoyle-ota"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    return data["tag_name"]


def checkout(tag: str) -> None:
    _run(["git", "-C", REPO_DIR, "fetch", "--tags", "origin"], timeout=60)
    result = _run(["git", "-C", REPO_DIR, "checkout", tag], timeout=30)
    if result.returncode != 0:
        raise RuntimeError("git checkout {} failed: {}".format(tag, result.stderr))


def reinstall_dependencies() -> None:
    pip = REPO_DIR + "/venv/bin/pip"
    result = _run([pip, "install", "-q", "-r", REPO_DIR + "/pi-zero/requirements.txt"], timeout=180)
    if result.returncode != 0:
        raise RuntimeError("pip install failed: {}".format(result.stderr))


def restart_service() -> None:
    _run(["systemctl", "restart", SERVICE_NAME], timeout=30)


def service_is_healthy() -> bool:
    for _ in range(HEALTH_CHECK_RETRIES):
        time.sleep(HEALTH_CHECK_DELAY_SECONDS)
        result = _run(["systemctl", "is-active", SERVICE_NAME], timeout=10)
        if result.stdout.strip() == "active":
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/etc/gargoyle/config.yaml")
    args = parser.parse_args()

    repo = _read_config_value(args.config, "ota_repo", "BenLBurke/haunted_mansion_gargoyle")
    ota_enabled = _read_config_value(args.config, "ota_enabled", "true")
    if ota_enabled.lower() in ("false", "no", "0"):
        print("ota_enabled is false in config, skipping update check")
        return 0

    before = current_tag()
    try:
        latest = latest_release_tag(repo)
    except Exception as exc:
        print("could not check for updates:", exc)
        return 0

    if before == latest:
        print("already on the latest release ({})".format(before))
        return 0

    print("update available ({} -> {}), applying...".format(before, latest))
    try:
        checkout(latest)
        reinstall_dependencies()
    except Exception as exc:
        print("update failed to apply, leaving the previous checkout in place:", exc)
        if before:
            checkout(before)
        return 1

    restart_service()
    if service_is_healthy():
        print("update to {} applied successfully".format(latest))
        return 0

    print("service did not come up healthy after updating to {} -- rolling back to {}".format(latest, before))
    if not before:
        print("WARNING: no previous tag recorded, cannot roll back automatically")
        return 1

    try:
        checkout(before)
        reinstall_dependencies()
        restart_service()
        if service_is_healthy():
            print("rollback to {} succeeded".format(before))
            return 1
        print("WARNING: rollback restart did not come up healthy either -- manual intervention needed")
    except Exception as exc:
        print("WARNING: rollback itself failed:", exc)
    return 1


if __name__ == "__main__":
    sys.exit(main())
