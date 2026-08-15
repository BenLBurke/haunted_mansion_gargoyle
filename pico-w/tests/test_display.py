import pytest

import display


def test_make_display_rejects_unknown_driver():
    config = {"display_driver": "vt100"}
    with pytest.raises(ValueError):
        display.make_display(config)
