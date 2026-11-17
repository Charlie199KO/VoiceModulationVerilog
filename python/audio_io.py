"""WAV file loading, mono conversion, resampling and saving."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import soundfile as sf

from . import config
from .fixed_point import float_to_int16, int16_to_float


def load_wav(path: str | Path, target_sample_rate: int = config.SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """Load a WAV file as mono signed PCM16 at target_sample_rate."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")
    audio, original_sr = sf.read(str(path), dtype="float32", always_2d=True)
    if audio.size == 0:
        raise ValueError("The selected audio file contains no samples.")
    if audio.shape[1] > 1:
        audio = np.mean(audio, axis=1, keepdims=True, dtype=np.float32)
    audio = audio[:, 0]
    if original_sr != target_sample_rate:
        try:
            from scipy.signal import resample_poly
            from math import gcd
            divisor = gcd(int(original_sr), int(target_sample_rate))
            up = target_sample_rate // divisor
            down = original_sr // divisor
            audio = resample_poly(audio, up, down).astype(np.float32)
        except ImportError as exc:
            raise RuntimeError("Resampling requires SciPy. Install project requirements.") from exc
    samples = float_to_int16(audio)
    return samples, int(target_sample_rate)


def save_wav(path: str | Path, samples: np.ndarray, sample_rate: int = config.SAMPLE_RATE) -> Path:
    """Save signed PCM16 samples as a mono WAV file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = np.asarray(samples)
    if np.issubdtype(raw.dtype, np.floating):
        data = float_to_int16(raw).reshape(-1)
    else:
        data = raw.astype(np.int16, copy=False).reshape(-1)
    sf.write(str(path), data, int(sample_rate), format="WAV", subtype="PCM_16")
    return path


def audio_file_info(path: str | Path) -> dict:
    info = sf.info(str(path))
    return {
        "samplerate": info.samplerate,
        "channels": info.channels,
        "frames": info.frames,
        "duration_seconds": info.duration,
        "format": info.format,
        "subtype": info.subtype,
    }


def samples_to_float(samples: np.ndarray) -> np.ndarray:
    return int16_to_float(samples)
