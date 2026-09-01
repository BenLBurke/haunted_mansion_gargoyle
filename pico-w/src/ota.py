# Over-the-air update client: checks GitHub for a newer tagged release,
# downloads the update to a staging area, verifies every file actually
# arrived, then swaps it into place -- keeping a backup so boot.py (which is
# never touched by updates) can automatically roll back if the new code
# doesn't boot.
#
# Deliberately conservative about what "correctly" means here: this
# protects against "the update doesn't boot" (verified download, swap with
# a kept backup, boot-confirmation with rollback) -- it does NOT protect
# against "the update boots fine but is subtly broken," which would need
# real monitoring/telemetry that's out of scope for a hobby device. See
# docs/OTA.md for the full explanation, including the one real gap: a
# syntax error bad enough to stop main.py from running at all means the
# device needs 1-2 power cycles for boot.py to notice and roll back, since
# there's no hardware watchdog forcing those cycles on its own.

import json

STAGING_DIR = "ota_staging"
BACKUP_DIR = "ota_backup"
PENDING_PATH = "ota_pending.json"
VERSION_PATH = "version.json"

GITHUB_API = "https://api.github.com"
RAW_GITHUB = "https://raw.githubusercontent.com"


def _current_version():
    try:
        with open(VERSION_PATH) as fh:
            return json.load(fh).get("version")
    except (OSError, ValueError):
        return None


def _latest_release_tag(repo):
    import requests

    url = "{}/repos/{}/releases/latest".format(GITHUB_API, repo)
    response = requests.get(url, timeout=15, headers={"User-Agent": "gargoyle-ota"})
    try:
        if response.status_code != 200:
            raise OSError("GitHub API returned HTTP {}".format(response.status_code))
        data = response.json()
    finally:
        response.close()
    return data["tag_name"]


def _fetch_manifest(repo, tag):
    import requests

    url = "{}/{}/{}/pico-w/ota_manifest.json".format(RAW_GITHUB, repo, tag)
    response = requests.get(url, timeout=15)
    try:
        if response.status_code != 200:
            raise OSError("manifest fetch returned HTTP {}".format(response.status_code))
        return response.json()
    finally:
        response.close()


def _ensure_dir(path):
    import os

    built = ""
    for part in path.split("/"):
        built = part if not built else built + "/" + part
        try:
            os.mkdir(built)
        except OSError:
            pass  # already exists


def _is_dir(path):
    import os

    try:
        os.listdir(path)
        return True
    except OSError:
        return False


def _clear_dir(path):
    import os

    try:
        entries = os.listdir(path)
    except OSError:
        return
    for name in entries:
        full = path + "/" + name
        if _is_dir(full):
            _clear_dir(full)
            try:
                os.rmdir(full)
            except OSError:
                pass
        else:
            try:
                os.remove(full)
            except OSError:
                pass


def _download_file(repo, tag, relpath, dest_path):
    import requests

    url = "{}/{}/{}/pico-w/src/{}".format(RAW_GITHUB, repo, tag, relpath)
    response = requests.get(url, timeout=20)
    try:
        if response.status_code != 200:
            raise OSError("{} returned HTTP {}".format(relpath, response.status_code))
        content = response.content
        if not content:
            raise OSError("{} downloaded empty".format(relpath))
        with open(dest_path, "wb") as fh:
            fh.write(content)
    finally:
        response.close()


def _stage_all(repo, tag, files):
    import os

    try:
        os.mkdir(STAGING_DIR)
    except OSError:
        pass

    for relpath in files:
        dest = STAGING_DIR + "/" + relpath
        if "/" in relpath:
            _ensure_dir(dest.rsplit("/", 1)[0])
        _download_file(repo, tag, relpath, dest)


def _swap_in(files):
    import os

    try:
        os.mkdir(BACKUP_DIR)
    except OSError:
        pass

    for relpath in files:
        live = relpath
        staged = STAGING_DIR + "/" + relpath
        backup = BACKUP_DIR + "/" + relpath

        if "/" in relpath:
            _ensure_dir(backup.rsplit("/", 1)[0])

        if _path_exists(live):
            try:
                os.remove(backup)
            except OSError:
                pass
            os.rename(live, backup)
        # else: nothing to back up -- this is a new file introduced by the release

        os.rename(staged, live)


def _path_exists(path):
    import os

    try:
        os.stat(path)
        return True
    except OSError:
        return False


def check_and_apply(config):
    """Checks for a newer release; if found, downloads, verifies, and swaps
    it in, then resets the device. Returns False if already up to date or
    the check/update failed -- failures here are logged and swallowed,
    never allowed to take down the running app."""
    repo = config["ota_repo"]
    current = _current_version()

    try:
        tag = _latest_release_tag(repo)
    except Exception as exc:
        print("OTA: could not check for updates:", exc)
        return False

    latest = tag[1:] if tag.startswith("v") else tag
    if current is not None and latest == current:
        return False

    print("OTA: update available ({} -> {}), downloading...".format(current, latest))
    try:
        manifest = _fetch_manifest(repo, tag)
        files = manifest["files"]
        _clear_dir(STAGING_DIR)
        _stage_all(repo, tag, files)
    except Exception as exc:
        print("OTA: update download failed, leaving current version in place:", exc)
        _clear_dir(STAGING_DIR)
        return False

    print("OTA: download verified, installing and restarting")
    _clear_dir(BACKUP_DIR)
    _swap_in(files)

    with open(PENDING_PATH, "w") as fh:
        json.dump({"from_version": current, "to_version": latest}, fh)

    import machine

    machine.reset()


def confirm_boot():
    """Call once, early in a successful boot. Clears the pending-update
    marker and its backup so a good update doesn't get needlessly rolled
    back later -- see boot.py for the other half of this, which rolls back
    if this *hasn't* run by the time a couple of boots have gone by."""
    if not _path_exists(PENDING_PATH):
        return

    print("OTA: confirming update booted successfully")
    import os

    for path in (PENDING_PATH, "ota_boot_attempts.json"):
        try:
            os.remove(path)
        except OSError:
            pass
    _clear_dir(BACKUP_DIR)
