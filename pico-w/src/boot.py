# Runs before main.py on every boot (standard MicroPython behavior). This
# file is deliberately excluded from ota_manifest.json and NEVER overwritten
# by an OTA update -- that's what makes rollback possible even if an update
# leaves main.py itself broken (e.g. a syntax error bad enough that none of
# main.py's own code, including its crash handler, ever runs). boot.py is
# guaranteed to still be the known-good version that originally shipped.
#
# ota.confirm_boot() (called early in main.py) clears the two files this
# checks for once a boot has gotten far enough to prove the update is
# basically sound. If that hasn't happened within MAX_ATTEMPTS boots, this
# restores the backed-up previous version instead of trying the broken one
# again.

import json

PENDING_PATH = "ota_pending.json"
ATTEMPTS_PATH = "ota_boot_attempts.json"
BACKUP_DIR = "ota_backup"
MAX_ATTEMPTS = 2


def _read_json(path, default):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _write_json(path, data):
    with open(path, "w") as fh:
        json.dump(data, fh)


def _remove(path):
    import os

    try:
        os.remove(path)
    except OSError:
        pass


def _is_dir(path):
    import os

    try:
        os.listdir(path)
        return True
    except OSError:
        return False


def _restore_backup(path, prefix_len):
    import os

    try:
        entries = os.listdir(path)
    except OSError:
        return

    for name in entries:
        full = path + "/" + name
        if _is_dir(full):
            _restore_backup(full, prefix_len)
        else:
            live_path = full[prefix_len:]
            try:
                os.remove(live_path)
            except OSError:
                pass
            os.rename(full, live_path)


def _rollback():
    print("boot.py: OTA update did not confirm within", MAX_ATTEMPTS, "boots -- rolling back")
    _restore_backup(BACKUP_DIR, len(BACKUP_DIR) + 1)
    _remove(PENDING_PATH)
    _remove(ATTEMPTS_PATH)


def check_and_maybe_rollback():
    """The whole boot.py decision: if there's no pending update, do nothing.
    Otherwise count this boot attempt, and roll back once too many boots
    have gone by without ota.confirm_boot() clearing the pending marker.
    Pulled out as a function (rather than bare top-level statements) so it
    can be exercised directly in tests, not just via module import."""
    pending = _read_json(PENDING_PATH, None)
    if pending is None:
        return

    attempts = _read_json(ATTEMPTS_PATH, {"count": 0})
    attempts["count"] += 1
    if attempts["count"] > MAX_ATTEMPTS:
        _rollback()
    else:
        _write_json(ATTEMPTS_PATH, attempts)


check_and_maybe_rollback()
