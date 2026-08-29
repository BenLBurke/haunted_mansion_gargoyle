import sys
import types

import renderer
import state


class FakeFB:
    def __init__(self):
        self.calls = []

    def _record(self, name):
        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return method

    def __getattr__(self, name):
        return self._record(name)


def _snapshot(wait_minutes=13, status="OPERATING"):
    attraction = state.AttractionStatus(status, wait_minutes)
    hours = state.ParkHours("9:00am", "11:00pm")
    return state.Snapshot(attraction, hours)


def test_label_scale_is_1_on_oled_dimensions():
    assert renderer._label_scale(128, 64) == 1


def test_label_scale_scales_up_on_tft_dimensions():
    # min(320//128, 240//64) == min(2, 3) == 2
    assert renderer._label_scale(320, 240) == 2


def test_label_scale_never_drops_below_1():
    assert renderer._label_scale(64, 32) == 1


def test_render_snapshot_on_oled_uses_plain_text_no_scaling_needed():
    fb = FakeFB()
    renderer.render_snapshot(fb, 128, 64, _snapshot(), "Disneyland", True)

    text_calls = [c for c in fb.calls if c[0] == "text"]
    assert any(call[1][0] == "DISNEYLAND" for call in text_calls)


def test_render_snapshot_on_tft_delegates_to_text_scale(monkeypatch):
    scaled_calls = []

    def fake_draw_scaled_text(fb, s, x, y, scale, color=1):
        scaled_calls.append((s, x, y, scale, color))

    fake_module = types.ModuleType("text_scale")
    fake_module.draw_scaled_text = fake_draw_scaled_text
    monkeypatch.setitem(sys.modules, "text_scale", fake_module)

    fb = FakeFB()
    renderer.render_snapshot(fb, 320, 240, _snapshot(), "Disneyland", True)

    assert scaled_calls, "expected the scaled-text path to be used at 320x240"
    label_call = next(c for c in scaled_calls if c[0] == "DISNEYLAND")
    assert label_call[3] == 2  # scale


def test_render_snapshot_shows_status_label_when_not_operating():
    fb = FakeFB()
    renderer.render_snapshot(fb, 128, 64, _snapshot(status="CLOSED"), "Disneyland", True)

    text_calls = [c[1][0] for c in fb.calls if c[0] == "text"]
    assert "CLOSED" in text_calls


def test_render_snapshot_marks_disconnected():
    fb = FakeFB()
    renderer.render_snapshot(fb, 128, 64, _snapshot(), "Disneyland", False)

    text_calls = [c[1][0] for c in fb.calls if c[0] == "text"]
    assert "!" in text_calls


def test_render_message_two_lines():
    fb = FakeFB()
    renderer.render_message(fb, 128, 64, "Waking up...", "please wait")

    text_calls = [c[1][0] for c in fb.calls if c[0] == "text"]
    assert "Waking up..." in text_calls
    assert "please wait" in text_calls
