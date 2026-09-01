import renderer


def test_unit_label_plural():
    assert renderer.unit_label(13) == "MINUTES"
    assert renderer.unit_label(0) == "MINUTES"


def test_unit_label_singular():
    assert renderer.unit_label(1) == "MINUTE"


def test_unit_label_eternity_easter_egg():
    assert renderer.unit_label(999) == "AN ETERNITY"
    assert renderer.unit_label(1500) == "AN ETERNITY"


def test_wrap_short_text_fits_one_line():
    assert renderer._wrap("Closed", 20) == ["Closed"]


def test_wrap_splits_on_word_boundaries():
    lines = renderer._wrap("Playful spooks have interrupted the tour", 12)
    assert all(len(line) <= 12 for line in lines)
    # every word survives the wrap, in order, none dropped or merged wrong
    assert " ".join(lines).split(" ") == "Playful spooks have interrupted the tour".split(" ")


def test_wrap_never_produces_empty_lines():
    lines = renderer._wrap("Unavoidably detained by pranky spirits", 10)
    assert all(line for line in lines)
