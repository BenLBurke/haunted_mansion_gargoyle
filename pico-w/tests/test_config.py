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


def test_defaults_use_spi_tft_not_i2c_oled():
    # The gothic-mansion redesign dropped SSD1306/I2C support in favor of
    # the 320x240 SPI TFT -- these keys should be gone, not just unused.
    for removed in ("i2c_id", "i2c_scl_pin", "i2c_sda_pin", "display_i2c_address"):
        assert removed not in gargoyle_config.DEFAULTS

    for key in ("spi_id", "spi_baudrate", "spi_sck_pin", "spi_mosi_pin",
                "spi_miso_pin", "spi_cs_pin", "spi_dc_pin", "spi_rst_pin"):
        assert key in gargoyle_config.DEFAULTS

    assert gargoyle_config.DEFAULTS["display_width"] == 320
    assert gargoyle_config.DEFAULTS["display_height"] == 240
