"""Fixed-point helpers shared by the Python reference and Verilog DSP core."""
from __future__ import annotations

import numpy as np

INT16_MIN = -32_768
INT16_MAX = 32_767


def saturate_int16(value: int) -> int:
    """Clamp an integer to the signed 16-bit PCM range."""
    value = int(value)
    if value > INT16_MAX:
        return INT16_MAX
    if value < INT16_MIN:
        return INT16_MIN
    return value


def saturate_array_int16(values: np.ndarray) -> np.ndarray:
    """Saturate an array and return int16 samples."""
    arr = np.asarray(values, dtype=np.int64)
    return np.clip(arr, INT16_MIN, INT16_MAX).astype(np.int16)


def float_to_int16(samples: np.ndarray) -> np.ndarray:
    """Convert normalized floating-point audio [-1, 1] to signed PCM16."""
    audio = np.asarray(samples, dtype=np.float64)
    audio = np.nan_to_num(audio, nan=0.0, posinf=1.0, neginf=-1.0)
    audio = np.clip(audio, -1.0, 1.0)
    # PCM16 convention: scale by 32768, then saturate +1.0 to +32767.
    # This also round-trips PCM16 WAV samples read by SoundFile as float32.
    scaled = np.rint(audio * 32768.0)
    return np.clip(scaled, INT16_MIN, INT16_MAX).astype(np.int16)


def int16_to_float(samples: np.ndarray) -> np.ndarray:
    """Convert signed PCM16 to normalized float32 audio."""
    arr = np.asarray(samples, dtype=np.int16)
    out = arr.astype(np.float32) / 32768.0
    return np.clip(out, -1.0, 1.0)


def q15_multiply(sample: int, gain_q15: int) -> int:
    """Multiply signed PCM by a non-negative Q1.15 gain.

    Python's right shift on a negative integer is an arithmetic shift, matching
    the >>> operation used in the Verilog reference implementation.
    """
    return saturate_int16((int(sample) * int(gain_q15)) >> 15)


def pcm16_to_hex(sample: int) -> str:
    """Return a four-digit two's-complement hexadecimal PCM16 word."""
    return f"{int(sample) & 0xFFFF:04X}"


def hex_to_pcm16(word: str) -> int:
    """Decode a 16-bit hexadecimal two's-complement value."""
    value = int(word.strip(), 16)
    if value < 0 or value > 0xFFFF:
        raise ValueError(f"Not a 16-bit hexadecimal word: {word!r}")
    return value - 0x10000 if value & 0x8000 else value
