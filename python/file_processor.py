"""High-level WAV processing for Python and Verilog simulation backends."""
from __future__ import annotations

from pathlib import Path
import numpy as np

from . import config
from .audio_io import load_wav, save_wav
from .dsp_effects import EffectParameters, PythonVoiceProcessor
from .verilog_bridge import VerilogBridge


def process_wav(input_path: str | Path, preset: str, backend: str = "python",
                parameters: EffectParameters | None = None,
                output_path: str | Path | None = None) -> tuple[np.ndarray, Path]:
    samples, sample_rate = load_wav(input_path, config.SAMPLE_RATE)
    params = parameters or EffectParameters()
    backend = backend.strip().lower()
    if backend == "python":
        processor = PythonVoiceProcessor(sample_rate)
        processed = processor.process_recorded(samples, preset, params)
    elif backend in {"verilog", "verilog simulation", "simulation"}:
        processed = VerilogBridge().process_samples(samples, preset, params)
    else:
        raise ValueError(f"Unknown processing backend: {backend}")

    if output_path is None:
        source = Path(input_path)
        output_path = config.OUTPUT_AUDIO_DIR / f"{source.stem}_{preset}_{backend.replace(' ', '_')}.wav"
    saved = save_wav(output_path, processed, sample_rate)
    return processed, saved
