import gargoyle_config


def test_load_missing_file_returns_defaults(tmp_path):
    config = gargoyle_config.load(str(tmp_path / "nope.json"))
    assert config["park"] == "disneyland"
    assert config["poll_interval_seconds"] == 60


def test_save_then_load_round_trips(tmp_path):
    path = str(tmp_path / "config.json")
    original = dict(gargoyle_config.DEFAULTS)
    original["park"] = "walt_disney_world"
    original["poll_interval_seconds"] = 120

    gargoyle_config.save(original, path)
    loaded = gargoyle_config.load(path)

    assert loaded["park"] == "walt_disney_world"
    assert loaded["poll_interval_seconds"] == 120


def test_load_ignores_unknown_fields(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"park": "disneyland", "not_a_real_field": 123}')

    config = gargoyle_config.load(str(path))

    assert config["park"] == "disneyland"
    assert "not_a_real_field" not in config


def test_load_fills_in_missing_fields_with_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"park": "walt_disney_world"}')

    config = gargoyle_config.load(str(path))

    assert config["park"] == "walt_disney_world"
    assert config["ap_ssid"] == gargoyle_config.DEFAULTS["ap_ssid"]
