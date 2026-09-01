import json

import boot


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)


def test_no_pending_update_does_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    boot.check_and_maybe_rollback()  # must not raise with no ota_pending.json present
    assert not (tmp_path / "ota_boot_attempts.json").exists()


def test_first_failed_boot_just_counts_the_attempt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / boot.PENDING_PATH, json.dumps({"from_version": "1.0.0", "to_version": "1.1.0"}))

    boot.check_and_maybe_rollback()

    assert (tmp_path / boot.PENDING_PATH).exists()  # not rolled back yet
    attempts = json.loads((tmp_path / boot.ATTEMPTS_PATH).read_text())
    assert attempts["count"] == 1


def test_rolls_back_after_max_attempts_exceeded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / boot.PENDING_PATH, json.dumps({"from_version": "1.0.0", "to_version": "1.1.0"}))
    _write(tmp_path / "main.py", "broken new version")
    _write(tmp_path / "lib" / "requests.py", "broken new version")
    _write(tmp_path / boot.BACKUP_DIR / "main.py", "good old version")
    _write(tmp_path / boot.BACKUP_DIR / "lib" / "requests.py", "good old version of requests.py")

    for _ in range(boot.MAX_ATTEMPTS):
        boot.check_and_maybe_rollback()
        assert (tmp_path / boot.PENDING_PATH).exists()  # still not rolled back

    boot.check_and_maybe_rollback()  # this is the attempt that exceeds MAX_ATTEMPTS

    assert not (tmp_path / boot.PENDING_PATH).exists()
    assert not (tmp_path / boot.ATTEMPTS_PATH).exists()
    assert (tmp_path / "main.py").read_text() == "good old version"
    assert (tmp_path / "lib" / "requests.py").read_text() == "good old version of requests.py"
    # Backup files were moved, not copied -- nothing left behind in ota_backup.
    assert not (tmp_path / boot.BACKUP_DIR / "main.py").exists()


def test_confirmed_update_is_never_rolled_back(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / boot.PENDING_PATH, json.dumps({"from_version": "1.0.0", "to_version": "1.1.0"}))
    _write(tmp_path / "main.py", "new version, works fine")
    _write(tmp_path / boot.BACKUP_DIR / "main.py", "old version")

    boot.check_and_maybe_rollback()  # attempt 1

    # ota.confirm_boot() would do this on a successful boot -- simulate it directly.
    (tmp_path / boot.PENDING_PATH).unlink()
    (tmp_path / boot.ATTEMPTS_PATH).unlink()

    for _ in range(boot.MAX_ATTEMPTS + 2):
        boot.check_and_maybe_rollback()

    assert (tmp_path / "main.py").read_text() == "new version, works fine"
