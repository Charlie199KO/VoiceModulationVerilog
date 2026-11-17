"""Run a recorded WAV file through the Verilog simulation and compare it."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python import config
from python.audio_io import load_wav, save_wav
from python.dsp_effects import EffectParameters, FixedPointDSP
from python.fixed_point import int16_to_float
from python.verification import compare_samples, format_report
from python.verilog_bridge import VerilogBridge
from python.voice_presets import verilog_mode_for


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Voice Modulator Verilog simulation.")
    parser.add_argument("--file", default="data/input_audio/demo_voice_like_tone.wav", help="Input WAV file")
    parser.add_argument("--preset", default="robot", choices=["normal", "robot", "echo", "radio", "volume"])
    parser.add_argument("--echo-ms", type=float, default=200.0)
    parser.add_argument("--echo-percent", type=float, default=40.0)
    parser.add_argument("--robot-hz", type=float, default=80.0)
    parser.add_argument("--volume-level", type=int, default=3, choices=range(5))
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path
    samples, _ = load_wav(input_path, config.SAMPLE_RATE)
    params = EffectParameters(
        ring_half_period_samples=max(1, round(config.SAMPLE_RATE / (2 * max(1.0, args.robot_hz)))),
        echo_delay_samples=min(config.ECHO_BUFFER_DEPTH - 1, max(1, round(args.echo_ms * config.SAMPLE_RATE / 1000.0))),
        echo_gain_q15=min(32767, max(0, round(args.echo_percent * 32768 / 100.0))),
        volume_level=args.volume_level,
    )

    reference_engine = FixedPointDSP(config.SAMPLE_RATE)
    reference = reference_engine.process_block(samples, verilog_mode_for(args.preset), params)
    try:
        actual = VerilogBridge().process_samples(samples, args.preset, params)
    except Exception as exc:
        print(f"Could not run Verilog simulation: {exc}")
        print("Check that Icarus Verilog is installed and both iverilog and vvp are on PATH.")
        return 1
    report = compare_samples(reference, actual)
    print(format_report(report))

    output_path = config.OUTPUT_AUDIO_DIR / f"{input_path.stem}_{args.preset}_verilog.wav"
    save_wav(output_path, actual, config.SAMPLE_RATE)
    print(f"Processed WAV: {output_path}")
    return 0 if report["exact_match"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
