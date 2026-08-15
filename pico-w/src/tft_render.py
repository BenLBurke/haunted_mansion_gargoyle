# Pure conversion/streaming logic for tft_screen.py, split into its own
# module (no framebuf import, no hardware) so it can be unit tested under
# CPython -- tft_screen.py itself imports framebuf at module level (same as
# the vendored ssd1306.py), which doesn't exist off-device.

CHUNK_ROWS = 8  # matches the vendored ili9341.Display.clear()'s own default


def build_lookup(fg_color, bg_color):
    """Pure function: 256-entry table mapping a MONO_HLSB byte (8 pixels,
    bit 7 = leftmost) to its 16-byte RGB565 equivalent."""
    fg = fg_color.to_bytes(2, "big")
    bg = bg_color.to_bytes(2, "big")
    lut = []
    for byte in range(256):
        row = bytearray(16)
        for bit in range(8):
            is_fg = (byte >> (7 - bit)) & 1
            pair = fg if is_fg else bg
            row[bit * 2] = pair[0]
            row[bit * 2 + 1] = pair[1]
        lut.append(bytes(row))
    return lut


def stream_to_tft(buffer, width, height, lut, block, chunk_rows=CHUNK_ROWS):
    """Converts a MONO_HLSB buffer to RGB565 and pushes it via `block(x0,
    y0, x1, y1, data)` (matching ili9341.Display.block's signature) in
    row-chunks small enough to stay RAM-safe -- a full 320x240 RGB565
    chunk buffer would be 150KB; an 8-row chunk is under 6KB. Takes `block`
    as a plain callable (not a Display instance) so it's testable against a
    fake recorder with no real hardware."""
    row_bytes = width // 8
    out = bytearray(width * 2 * chunk_rows)
    for chunk_y in range(0, height, chunk_rows):
        rows = min(chunk_rows, height - chunk_y)
        pos = 0
        for r in range(rows):
            base = (chunk_y + r) * row_bytes
            for i in range(row_bytes):
                out[pos : pos + 16] = lut[buffer[base + i]]
                pos += 16
        block(0, chunk_y, width - 1, chunk_y + rows - 1, memoryview(out)[:pos])
