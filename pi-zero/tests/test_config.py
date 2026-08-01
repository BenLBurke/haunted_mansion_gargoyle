from pathlib import Path

from gargoyle.config import Config


def test_load_missing_file_returns_defaults(tmp_path):
    config = Config.load(tmp_path / "nope.yaml")
    assert config.park == "disneyland"
    assert config.poll_interval_seconds == 60


def test_save_then_load_round_trips(tmp_path: Path):
    path = tmp_path / "config.yaml"
    original = Config(park="walt_disney_world", poll_interval_seconds=120, volume=0.5)
    original.save(path)

    loaded = Config.load(path)

    assert loaded.park == "walt_disney_world"
    assert loaded.poll_interval_seconds == 120
    assert loaded.volume == 0.5


def test_load_ignores_unknown_fields(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("park: disneyland\nnot_a_real_field: 123\n")

    config = Config.load(path)

    assert config.park == "disneyland"


def test_park_info_resolves_registry_entry():
    config = Config(park="disneyland")
    info = config.park_info()
    assert info.label == "Disneyland Park (Anaheim)"
