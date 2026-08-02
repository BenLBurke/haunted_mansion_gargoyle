import json

import ota


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_current_version_reads_version_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "version.json", json.dumps({"version": "1.2.3"}))
    assert ota._current_version() == "1.2.3"


def test_current_version_missing_file_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert ota._current_version() is None


def test_current_version_corrupt_file_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "version.json", "not valid json")
    assert ota._current_version() is None


def test_path_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "somefile.py", "x = 1")
    assert ota._path_exists("somefile.py") is True
    assert ota._path_exists("nope.py") is False


def test_is_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "adir").mkdir()
    _write(tmp_path / "afile.py", "x = 1")
    assert ota._is_dir("adir") is True
    assert ota._is_dir("afile.py") is False
    assert ota._is_dir("nope") is False


def test_ensure_dir_creates_nested_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ota._ensure_dir("a/b/c")
    assert (tmp_path / "a" / "b" / "c").is_dir()


def test_clear_dir_removes_files_and_subdirectories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "staging" / "main.py", "x")
    _write(tmp_path / "staging" / "lib" / "requests.py", "y")

    ota._clear_dir("staging")

    assert (tmp_path / "staging").exists()  # the directory itself is kept, just emptied
    assert list((tmp_path / "staging").iterdir()) == []


def test_clear_dir_on_missing_directory_does_not_raise(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ota._clear_dir("does_not_exist")  # must not raise


def test_swap_in_backs_up_existing_files_and_installs_staged_ones(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "main.py", "old main")
    _write(tmp_path / "lib" / "requests.py", "old requests")
    _write(tmp_path / ota.STAGING_DIR / "main.py", "new main")
    _write(tmp_path / ota.STAGING_DIR / "lib" / "requests.py", "new requests")
    _write(tmp_path / ota.STAGING_DIR / "brand_new_file.py", "a file this release adds")

    ota._swap_in(["main.py", "lib/requests.py", "brand_new_file.py"])

    assert (tmp_path / "main.py").read_text() == "new main"
    assert (tmp_path / "lib" / "requests.py").read_text() == "new requests"
    assert (tmp_path / "brand_new_file.py").read_text() == "a file this release adds"
    assert (tmp_path / ota.BACKUP_DIR / "main.py").read_text() == "old main"
    assert (tmp_path / ota.BACKUP_DIR / "lib" / "requests.py").read_text() == "old requests"
    # A file with no prior live version has nothing to back up.
    assert not (tmp_path / ota.BACKUP_DIR / "brand_new_file.py").exists()


def test_check_and_apply_skips_when_already_up_to_date(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "version.json", json.dumps({"version": "1.0.0"}))
    monkeypatch.setattr(ota, "_latest_release_tag", lambda repo: "v1.0.0")

    result = ota.check_and_apply({"ota_repo": "someone/somerepo"})

    assert result is False


def test_check_and_apply_returns_false_when_release_check_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def _boom(repo):
        raise OSError("network down")

    monkeypatch.setattr(ota, "_latest_release_tag", _boom)

    result = ota.check_and_apply({"ota_repo": "someone/somerepo"})

    assert result is False


def test_confirm_boot_clears_pending_marker_and_backup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / ota.PENDING_PATH, json.dumps({"from_version": "1.0.0", "to_version": "1.1.0"}))
    _write(tmp_path / "ota_boot_attempts.json", json.dumps({"count": 1}))
    _write(tmp_path / ota.BACKUP_DIR / "main.py", "old main")

    ota.confirm_boot()

    assert not (tmp_path / ota.PENDING_PATH).exists()
    assert not (tmp_path / "ota_boot_attempts.json").exists()
    assert list((tmp_path / ota.BACKUP_DIR).iterdir()) == []


def test_confirm_boot_does_nothing_when_no_update_pending(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ota.confirm_boot()  # must not raise with nothing pending
