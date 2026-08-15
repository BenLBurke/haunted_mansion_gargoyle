import tft_render


class FakeBlock:
    """Records each block(x0, y0, x1, y1, data) call, copying the data
    since stream_to_tft reuses the same bytearray across chunks."""

    def __init__(self):
        self.calls = []

    def __call__(self, x0, y0, x1, y1, data):
        self.calls.append((x0, y0, x1, y1, bytes(data)))


def test_build_lookup_all_foreground_byte():
    lut = tft_render.build_lookup(0xFFFF, 0x0000)
    assert lut[0xFF] == b"\xff\xff" * 8


def test_build_lookup_all_background_byte():
    lut = tft_render.build_lookup(0xFFFF, 0x0000)
    assert lut[0x00] == b"\x00\x00" * 8


def test_build_lookup_bit_order_is_msb_first():
    # 0b10000000 -> leftmost pixel (bit 7) is foreground, the rest background.
    lut = tft_render.build_lookup(0xFD20, 0x0012)
    fg = (0xFD20).to_bytes(2, "big")
    bg = (0x0012).to_bytes(2, "big")
    expected = fg + bg * 7
    assert lut[0b10000000] == expected


def test_build_lookup_has_256_entries():
    lut = tft_render.build_lookup(0x1234, 0x5678)
    assert len(lut) == 256


def test_stream_to_tft_single_chunk_small_image():
    # 8 wide x 8 tall, 1 chunk (chunk_rows defaults to 8) -- one block() call.
    width, height = 8, 8
    lut = tft_render.build_lookup(0xFFFF, 0x0000)
    buffer = bytes([0xFF] * height)  # every row fully foreground
    block = FakeBlock()

    tft_render.stream_to_tft(buffer, width, height, lut, block)

    assert len(block.calls) == 1
    x0, y0, x1, y1, data = block.calls[0]
    assert (x0, y0, x1, y1) == (0, 0, 7, 7)
    assert data == (b"\xff\xff" * 8) * 8


def test_stream_to_tft_multiple_chunks_covers_full_height():
    width, height = 8, 20  # 20 rows / 8-row chunks -> chunks of 8, 8, 4
    lut = tft_render.build_lookup(0xFFFF, 0x0000)
    buffer = bytes([0x00] * height)
    block = FakeBlock()

    tft_render.stream_to_tft(buffer, width, height, lut, block, chunk_rows=8)

    assert [(c[1], c[3]) for c in block.calls] == [(0, 7), (8, 15), (16, 19)]
    # last chunk is only 4 rows tall -- data length should reflect that, not
    # leak stale bytes from the reused scratch buffer.
    assert len(block.calls[-1][4]) == width * 2 * 4


def test_stream_to_tft_mixed_pixels_round_trip():
    width, height = 8, 1
    fg, bg = 0xABCD, 0x1234
    lut = tft_render.build_lookup(fg, bg)
    buffer = bytes([0b11001010])
    block = FakeBlock()

    tft_render.stream_to_tft(buffer, width, height, lut, block)

    fg_b = fg.to_bytes(2, "big")
    bg_b = bg.to_bytes(2, "big")
    bits = [1, 1, 0, 0, 1, 0, 1, 0]
    expected = b"".join(fg_b if b else bg_b for b in bits)
    assert block.calls[0][4] == expected
