"""Generate a short synthetic voice-like test tone for DSP demonstrations."""
from pathlib import Path
import sys
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python import config
from python.audio_io import save_wav


def main() -> None:
    duration = 4.0
    sample_rate = config.SAMPLE_RATE
    t = np.arange(int(duration * sample_rate), dtype=np.float64) / sample_rate
    # A voiced-like harmonic signal with a slowly changing envelope.
    fundamental = 145.0
    signal = (
        0.42 * np.sin(2 * np.pi * fundamental * t)
        + 0.20 * np.sin(2 * np.pi * 2 * fundamental * t)
        + 0.11 * np.sin(2 * np.pi * 3 * fundamental * t)
        + 0.06 * np.sin(2 * np.pi * 5 * fundamental * t)
    )
    envelope = 0.55 + 0.35 * np.sin(2 * np.pi * 1.4 * t) ** 2
    signal *= envelope
    signal[: int(0.15 * sample_rate)] = 0.0
    output = config.INPUT_AUDIO_DIR / "demo_voice_like_tone.wav"
    save_wav(output, signal, sample_rate)
    print(f"Created: {output}")
    print("This is a synthetic test tone, not a speech recording.")


if __name__ == "__main__":
    main()
