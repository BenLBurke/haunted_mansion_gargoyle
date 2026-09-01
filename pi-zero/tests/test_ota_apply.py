from unittest.mock import MagicMock, patch

import ota_apply


def test_read_config_value_finds_key(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("park: disneyland\nota_check_interval_hours: 12\n")
    assert ota_apply._read_config_value(str(config), "ota_check_interval_hours", "24") == "12"


def test_read_config_value_falls_back_when_key_missing(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("park: disneyland\n")
    assert ota_apply._read_config_value(str(config), "ota_check_interval_hours", "24") == "24"


def test_read_config_value_falls_back_when_file_missing(tmp_path):
    assert ota_apply._read_config_value(str(tmp_path / "nope.yaml"), "ota_repo", "default") == "default"


def _completed(returncode=0, stdout="", stderr=""):
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def test_current_tag_returns_none_when_head_is_not_a_tag():
    with patch("ota_apply._run", return_value=_completed(returncode=1)):
        assert ota_apply.current_tag() is None


def test_current_tag_returns_the_tag_name():
    with patch("ota_apply._run", return_value=_completed(returncode=0, stdout="v1.0.0\n")):
        assert ota_apply.current_tag() == "v1.0.0"


def test_main_skips_when_already_on_latest(tmp_path, capsys):
    config = tmp_path / "config.yaml"
    config.write_text("ota_repo: someone/somerepo\nota_enabled: true\n")

    with (
        patch("sys.argv", ["ota_apply.py", "--config", str(config)]),
        patch("ota_apply.current_tag", return_value="v1.0.0"),
        patch("ota_apply.latest_release_tag", return_value="v1.0.0"),
        patch("ota_apply.checkout") as checkout,
        patch("ota_apply.restart_service") as restart,
    ):
        exit_code = ota_apply.main()

    assert exit_code == 0
    checkout.assert_not_called()
    restart.assert_not_called()
    assert "already on the latest release" in capsys.readouterr().out


def test_main_skips_entirely_when_ota_disabled(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("ota_enabled: false\n")

    with (
        patch("sys.argv", ["ota_apply.py", "--config", str(config)]),
        patch("ota_apply.latest_release_tag") as latest,
    ):
        exit_code = ota_apply.main()

    assert exit_code == 0
    latest.assert_not_called()


def test_main_returns_zero_when_release_check_fails(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("ota_repo: someone/somerepo\n")

    with (
        patch("sys.argv", ["ota_apply.py", "--config", str(config)]),
        patch("ota_apply.current_tag", return_value="v1.0.0"),
        patch("ota_apply.latest_release_tag", side_effect=OSError("network down")),
    ):
        exit_code = ota_apply.main()

    assert exit_code == 0  # a failed check is not treated as an update failure


def test_main_applies_update_and_confirms_when_service_comes_up_healthy(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("ota_repo: someone/somerepo\n")

    with (
        patch("sys.argv", ["ota_apply.py", "--config", str(config)]),
        patch("ota_apply.current_tag", return_value="v1.0.0"),
        patch("ota_apply.latest_release_tag", return_value="v1.1.0"),
        patch("ota_apply.checkout") as checkout,
        patch("ota_apply.reinstall_dependencies") as reinstall,
        patch("ota_apply.restart_service") as restart,
        patch("ota_apply.service_is_healthy", return_value=True),
    ):
        exit_code = ota_apply.main()

    assert exit_code == 0
    checkout.assert_called_once_with("v1.1.0")
    reinstall.assert_called_once()
    restart.assert_called_once()


def test_main_rolls_back_when_service_does_not_come_up_healthy(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("ota_repo: someone/somerepo\n")

    checkout_calls = []

    def fake_checkout(tag):
        checkout_calls.append(tag)

    with (
        patch("sys.argv", ["ota_apply.py", "--config", str(config)]),
        patch("ota_apply.current_tag", return_value="v1.0.0"),
        patch("ota_apply.latest_release_tag", return_value="v1.1.0"),
        patch("ota_apply.checkout", side_effect=fake_checkout),
        patch("ota_apply.reinstall_dependencies"),
        patch("ota_apply.restart_service"),
        patch("ota_apply.service_is_healthy", side_effect=[False, True]),
    ):
        exit_code = ota_apply.main()

    assert exit_code == 1
    # First checks out the new release, then rolls back to the previous one.
    assert checkout_calls == ["v1.1.0", "v1.0.0"]


def test_main_warns_but_does_not_crash_when_rollback_has_no_previous_tag(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("ota_repo: someone/somerepo\n")

    with (
        patch("sys.argv", ["ota_apply.py", "--config", str(config)]),
        patch("ota_apply.current_tag", return_value=None),
        patch("ota_apply.latest_release_tag", return_value="v1.1.0"),
        patch("ota_apply.checkout"),
        patch("ota_apply.reinstall_dependencies"),
        patch("ota_apply.restart_service"),
        patch("ota_apply.service_is_healthy", return_value=False),
    ):
        exit_code = ota_apply.main()

    assert exit_code == 1
