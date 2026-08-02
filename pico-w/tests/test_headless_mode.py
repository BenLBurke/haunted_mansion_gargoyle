from audio import NullSoundPlayer
from display import ConsoleScreen
from state import AttractionStatus, ParkHours, Snapshot


def test_null_sound_player_does_not_raise(capsys):
    player = NullSoundPlayer()
    player.play("startup")
    assert "startup" in capsys.readouterr().out


def test_console_screen_show_snapshot_operating(capsys):
    screen = ConsoleScreen()
    snapshot = Snapshot(AttractionStatus("OPERATING", 35), ParkHours("9:00am", "11:00pm"))
    screen.show_snapshot(snapshot, "Disneyland", True)
    out = capsys.readouterr().out
    assert "35 min wait" in out
    assert "Disneyland" in out


def test_console_screen_show_snapshot_closed(capsys):
    screen = ConsoleScreen()
    snapshot = Snapshot(AttractionStatus("CLOSED", None), None)
    screen.show_snapshot(snapshot, "Magic Kingdom", False)
    out = capsys.readouterr().out
    assert "CLOSED" in out
    assert "connected=False" in out


def test_console_screen_show_message_and_animation_do_not_raise(capsys):
    screen = ConsoleScreen()
    screen.show_message("Waking up...")
    screen.show_message("Lost the signal...", "retrying")
    screen.play_wait_time_change_animation()
    out = capsys.readouterr().out
    assert "Waking up" in out
    assert "retrying" in out
