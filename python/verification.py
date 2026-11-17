"""Sample-by-sample Python reference versus Verilog simulation verification."""
from __future__ import annotations

from dataclasses import asdict
import numpy as np

from . import config
from .audio_io import load_wav
from .dsp_effects import EffectParameters, FixedPointDSP
from .verilog_bridge import VerilogBridge
from .voice_presets import verilog_mode_for


def compare_samples(reference: np.ndarray, actual: np.ndarray) -> dict:
    reference = np.asarray(reference, dtype=np.int16).reshape(-1)
    actual = np.asarray(actual, dtype=np.int16).reshape(-1)
    count_match = reference.size == actual.size
    overlap = min(reference.size, actual.size)
    differences = np.abs(reference[:overlap].astype(np.int32) - actual[:overlap].astype(np.int32))
    mismatch_indices = np.flatnonzero(differences != 0)
    return {
        "reference_samples": int(reference.size),
        "verilog_samples": int(actual.size),
        "sample_count_match": bool(count_match),
        "matching_samples": int(overlap - mismatch_indices.size),
        "mismatched_samples": int(mismatch_indices.size + abs(reference.size - actual.size)),
        "first_mismatch_index": int(mismatch_indices[0]) if mismatch_indices.size else None,
        "maximum_absolute_difference": int(differences.max()) if differences.size else 0,
        "exact_match": bool(count_match and mismatch_indices.size == 0),
    }


def verify_samples(samples: np.ndarray, preset: str,
                   parameters: EffectParameters | None = None,
                   bridge: VerilogBridge | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    p = parameters or EffectParameters()
    reference_engine = FixedPointDSP(config.SAMPLE_RATE)
    reference = reference_engine.process_block(samples, verilog_mode_for(preset), p)
    actual = (bridge or VerilogBridge()).process_samples(samples, preset, p)
    return reference, actual, compare_samples(reference, actual)


def verify_wav(path: str, preset: str,
               parameters: EffectParameters | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    samples, _ = load_wav(path, config.SAMPLE_RATE)
    return verify_samples(samples, preset, parameters)


def format_report(report: dict) -> str:
    lines = [
        "VOICE MODULATOR — PYTHON / VERILOG VERIFICATION",
        "=" * 52,
        f"Python reference samples : {report['reference_samples']}",
        f"Verilog output samples   : {report['verilog_samples']}",
        f"Sample counts match      : {report['sample_count_match']}",
        f"Matching samples         : {report['matching_samples']}",
        f"Mismatched samples       : {report['mismatched_samples']}",
        f"First mismatch index     : {report['first_mismatch_index']}",
        f"Maximum absolute diff.   : {report['maximum_absolute_difference']}",
        f"Exact match              : {report['exact_match']}",
    ]
    return "\n".join(lines)
