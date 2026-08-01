# Streams WAV files out over I2S to a MAX98357A amp. Reads and parses just
# enough of the RIFF/WAVE header to configure I2S correctly, then streams
# the data chunk in fixed-size blocks -- no wave module (MicroPython doesn't
# ship the CPython one) and no full-file buffering (there isn't the RAM).

import struct

SOUNDS_DIR = "sounds"
CUES = ("startup", "wait_increased", "wait_decreased", "park_open", "park_close", "error")


def _read_wav_header(f):
    riff = f.read(12)
    if riff[0:4] != b"RIFF" or riff[8:12] != b"WAVE":
        raise ValueError("not a WAV file")

    fmt = None
    while True:
        chunk_header = f.read(8)
        if len(chunk_header) < 8:
            raise ValueError("missing data chunk")
        chunk_id = chunk_header[0:4]
        chunk_size = struct.unpack("<I", chunk_header[4:8])[0]

        if chunk_id == b"fmt ":
            fmt_data = f.read(chunk_size)
            if chunk_size % 2:
                f.read(1)  # RIFF chunks are padded to an even size
            channels, sample_rate, _, _, _, bits_per_sample = struct.unpack("<HHIIHH", fmt_data[:16])
            fmt = (channels, sample_rate, bits_per_sample)
        elif chunk_id == b"data":
            if fmt is None:
                raise ValueError("data chunk arrived before fmt chunk")
            channels, sample_rate, bits_per_sample = fmt
            return channels, sample_rate, bits_per_sample, chunk_size
        else:
            f.read(chunk_size)
            if chunk_size % 2:
                f.read(1)


class SoundPlayer:
    def __init__(self, i2s_id, sck_pin, ws_pin, sd_pin, sounds_dir=SOUNDS_DIR):
        self._i2s_id = i2s_id
        self._sck_pin = sck_pin
        self._ws_pin = ws_pin
        self._sd_pin = sd_pin
        self._sounds_dir = sounds_dir
        self._i2s = None
        self._i2s_format = None  # (sample_rate, bits, channels) currently configured

    def play(self, cue):
        if cue not in CUES:
            raise ValueError("Unknown sound cue '{}'".format(cue))
        path = "{}/{}.wav".format(self._sounds_dir, cue)
        try:
            f = open(path, "rb")
        except OSError:
            print("(sound cue '{}' not played: {} missing)".format(cue, path))
            return

        try:
            channels, sample_rate, bits, data_size = _read_wav_header(f)
            if bits not in (16, 32):
                raise ValueError("unsupported sample width: {} bits".format(bits))
            self._ensure_i2s(sample_rate, bits, channels)

            remaining = data_size
            buf = bytearray(2048)
            mv = memoryview(buf)
            while remaining > 0:
                to_read = min(len(buf), remaining)
                n = f.readinto(mv[:to_read])
                if not n:
                    break
                self._i2s.write(mv[:n])
                remaining -= n
        except (OSError, ValueError) as exc:
            print("failed to play sound cue '{}': {}".format(cue, exc))
        finally:
            f.close()

    def _ensure_i2s(self, sample_rate, bits, channels):
        fmt_key = (sample_rate, bits, channels)
        if self._i2s is not None and self._i2s_format == fmt_key:
            return

        from machine import I2S, Pin

        if self._i2s is not None:
            self._i2s.deinit()

        audio_format = I2S.STEREO if channels == 2 else I2S.MONO
        self._i2s = I2S(
            self._i2s_id,
            sck=Pin(self._sck_pin),
            ws=Pin(self._ws_pin),
            sd=Pin(self._sd_pin),
            mode=I2S.TX,
            bits=bits,
            format=audio_format,
            rate=sample_rate,
            ibuf=8000,
        )
        self._i2s_format = fmt_key


class NullSoundPlayer:
    """Stands in for SoundPlayer when audio_enabled is False -- prints the
    cue name to the serial console instead, for bring-up testing on a
    breadboard before the amp/speaker is wired up."""

    def play(self, cue):
        print("[sound] {}".format(cue))
