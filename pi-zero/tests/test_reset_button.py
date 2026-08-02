from unittest.mock import MagicMock

from gargoyle.reset_button import MockButton, factory_reset, make_reset_button


def test_make_reset_button_returns_mock_when_simulating():
    button = make_reset_button(22, 3.0, lambda: None, simulate=True)
    assert isinstance(button, MockButton)
    assert button.pin == 22
    assert button.hold_time == 3.0


def test_factory_reset_forgets_wifi_and_reboots(monkeypatch):
    forget_mock = MagicMock()
    reboot_mock = MagicMock()
    monkeypatch.setattr("gargoyle.reset_button.network.forget_all_wifi_connections", forget_mock)
    monkeypatch.setattr("gargoyle.reset_button.network.reboot", reboot_mock)

    factory_reset()

    forget_mock.assert_called_once()
    reboot_mock.assert_called_once()
