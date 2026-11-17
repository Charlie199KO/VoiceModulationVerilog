"""Voice effects and deterministic fixed-point DSP reference model.

The FixedPointDSP class mirrors the five Verilog simulation modes:
0 bypass, 1 robot/ring modulation, 2 echo, 3 radio filter, 4 volume.
The higher-level PythonVoiceProcessor also provides Python-only pitch styles.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from . import config
from .fixed_point import (
    float_to_int16,
    int16_to_float,
    saturate_int16,
    saturate_array_int16,
)


@dataclass
class EffectParameters:
    ring_half_period_samples: int = config.DEFAULT_RING_HALF_PERIOD
    echo_delay_samples: int = config.DEFAULT_ECHO_DELAY_SAMPLES
    echo_gain_q15: int = config.DEFAULT_ECHO_GAIN_Q15
    volume_level: int = config.DEFAULT_VOLUME_LEVEL


class FixedPointDSP:
    """Sample-by-sample fixed-point reference matching the Verilog DSP core.

    Every processing branch advances for every accepted input sample. This
    mirrors voice_dsp_core.v, where all effect modules receive sample_valid
    continuously and the mode selector chooses the corresponding result.
    """

    def __init__(self, sample_rate: int = config.SAMPLE_RATE):
        if sample_rate != config.SAMPLE_RATE:
            raise ValueError(
                f"The Verilog reference uses {config.SAMPLE_RATE} Hz. "
                "Resample audio before using this fixed-point backend."
            )
        self.sample_rate = sample_rate
        self.reset()

    def reset(self) -> None:
        self.ring_count = 0
        self.ring_sign = 1
        self.echo_memory = np.zeros(config.ECHO_BUFFER_DEPTH, dtype=np.int16)
        self.echo_write_ptr = 0
        self.radio_x_prev = 0
        self.radio_hp_prev = 0
        self.radio_lp_prev = 0

    @staticmethod
    def _volume(sample: int, level: int) -> int:
        level = int(level)
        if level == 0:        # mute
            return 0
        if level == 1:        # 25%; arithmetic shift matches Verilog >>> 2
            return saturate_int16(sample >> 2)
        if level == 2:        # 50%
            return saturate_int16(sample >> 1)
        if level == 3:        # 100%
            return saturate_int16(sample)
        if level == 4:        # 200%, saturating after left shift
            return saturate_int16(sample << 1)
        return saturate_int16(sample)

    def _ring(self, sample: int, half_period_samples: int) -> int:
        half_period = max(1, int(half_period_samples))
        result = sample if self.ring_sign > 0 else saturate_int16(-sample)
        if self.ring_count >= half_period - 1:
            self.ring_count = 0
            self.ring_sign *= -1
        else:
            self.ring_count += 1
        return result

    def _echo(self, sample: int, delay_samples: int, gain_q15: int) -> int:
        delay = min(max(1, int(delay_samples)), config.ECHO_BUFFER_DEPTH - 1)
        gain = min(max(0, int(gain_q15)), 32_767)
        read_ptr = (self.echo_write_ptr - delay) % config.ECHO_BUFFER_DEPTH
        delayed = int(self.echo_memory[read_ptr])
        echo_component = (delayed * gain) >> 15
        result = saturate_int16(sample + echo_component)
        self.echo_memory[self.echo_write_ptr] = np.int16(sample)
        self.echo_write_ptr = (self.echo_write_ptr + 1) % config.ECHO_BUFFER_DEPTH
        return result

    def _radio(self, sample: int) -> int:
        hp_delta = self.radio_hp_prev + sample - self.radio_x_prev
        hp_next = (hp_delta * config.RADIO_ALPHA_HP_Q15) >> 15
        lp_delta = hp_next - self.radio_lp_prev
        lp_next = self.radio_lp_prev + ((lp_delta * config.RADIO_ALPHA_LP_Q15) >> 15)
        self.radio_x_prev = sample
        self.radio_hp_prev = hp_next
        self.radio_lp_prev = lp_next
        return saturate_int16(lp_next)

    def process_sample(self, sample: int, mode: int,
                       parameters: EffectParameters | None = None) -> int:
        p = parameters or EffectParameters()
        x = saturate_int16(sample)

        # Advance all paths on every accepted sample, as the Verilog core does.
        bypass_value = x
        robot_value = self._ring(x, p.ring_half_period_samples)
        echo_value = self._echo(x, p.echo_delay_samples, p.echo_gain_q15)
        radio_value = self._radio(x)
        volume_value = self._volume(x, p.volume_level)

        mode = int(mode)
        if mode == config.MODE_BYPASS:
            return bypass_value
        if mode == config.MODE_ROBOT:
            return robot_value
        if mode == config.MODE_ECHO:
            return echo_value
        if mode == config.MODE_RADIO:
            return radio_value
        if mode == config.MODE_VOLUME:
            return volume_value
        return bypass_value

    def process_block(self, samples: np.ndarray, mode: int,
                      parameters: EffectParameters | None = None) -> np.ndarray:
        input_samples = np.asarray(samples, dtype=np.int16).reshape(-1)
        output = np.empty(input_samples.size, dtype=np.int16)
        p = parameters or EffectParameters()
        for index, sample in enumerate(input_samples):
            output[index] = self.process_sample(int(sample), mode, p)
        return output


class PythonVoiceProcessor:
    """High-level Python processor for live and recorded voice effects."""

    PYTHON_PRESETS = {"deep", "cartoon", "higher", "cinematic"}
    FIXED_PRESETS = set(config.MODE_NAMES)

    def __init__(self, sample_rate: int = config.SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.fixed_dsp = FixedPointDSP(sample_rate=sample_rate)
        self.parameters = EffectParameters()
        self._cinematic_echo = FixedPointDSP(sample_rate)
        self._last_pitch_tail: np.ndarray | None = None

    def reset(self) -> None:
        self.fixed_dsp.reset()
        self._cinematic_echo.reset()
        self._last_pitch_tail = None

    @staticmethod
    def preset_to_mode(preset: str) -> int:
        name = preset.strip().lower()
        if name not in config.MODE_NAMES:
            raise ValueError(f"Preset {preset!r} is not supported by the Verilog backend.")
        return config.MODE_NAMES[name]

    def process_fixed(self, samples: np.ndarray, preset: str,
                      parameters: EffectParameters | None = None) -> np.ndarray:
        mode = self.preset_to_mode(preset)
        return self.fixed_dsp.process_block(samples, mode, parameters or self.parameters)

    def _pitch_shift(self, samples: np.ndarray, semitones: float) -> np.ndarray:
        try:
            import librosa
        except ImportError as exc:
            raise RuntimeError(
                "Pitch shifting requires librosa. Install the project requirements."
            ) from exc

        pcm = np.asarray(samples, dtype=np.int16).reshape(-1)
        if pcm.size == 0:
            return pcm.copy()
        audio = int16_to_float(pcm)
        shifted = librosa.effects.pitch_shift(
            y=audio,
            sr=self.sample_rate,
            n_steps=float(semitones),
            bins_per_octave=12,
        )
        shifted = np.asarray(shifted, dtype=np.float32)
        # librosa should preserve duration; enforce the original length defensively.
        if shifted.size < pcm.size:
            shifted = np.pad(shifted, (0, pcm.size - shifted.size))
        elif shifted.size > pcm.size:
            shifted = shifted[:pcm.size]
        return float_to_int16(shifted)

    def process_recorded(self, samples: np.ndarray, preset: str,
                         parameters: EffectParameters | None = None) -> np.ndarray:
        """Process a complete recording. Advanced pitch effects are Python-only."""
        name = preset.strip().lower()
        p = parameters or self.parameters
        self.reset()
        if name in self.FIXED_PRESETS:
            return self.process_fixed(samples, name, p)
        if name == "deep":
            return self._pitch_shift(samples, -5.0)
        if name == "cartoon":
            return self._pitch_shift(samples, 7.0)
        if name == "higher":
            return self._pitch_shift(samples, 3.0)
        if name == "cinematic":
            pitched = self._pitch_shift(samples, -2.0)
            echo_engine = FixedPointDSP(self.sample_rate)
            return echo_engine.process_block(
                pitched, config.MODE_ECHO,
                EffectParameters(
                    echo_delay_samples=int(0.14 * self.sample_rate),
                    echo_gain_q15=8_192,
                ),
            )
        raise ValueError(f"Unknown voice preset: {preset}")

    def process_live_block(self, samples: np.ndarray, preset: str,
                           parameters: EffectParameters | None = None) -> np.ndarray:
        """Process one microphone block.

        The fixed-point effects are lightweight. Pitch effects use librosa on
        blocks and can add latency/artifacts; they are experimental in live mode.
        """
        name = preset.strip().lower()
        p = parameters or self.parameters
        pcm = np.asarray(samples, dtype=np.int16).reshape(-1)
        if name in self.FIXED_PRESETS:
            mode = self.preset_to_mode(name)
            return self.fixed_dsp.process_block(pcm, mode, p)
        if name in self.PYTHON_PRESETS:
            # Keep the fixed-point effect states advancing while a Python-only
            # pitch preset is selected, so switching back to a Verilog effect
            # does not leave stale ring/echo/filter state.
            self.fixed_dsp.process_block(pcm, config.MODE_BYPASS, p)
            steps = {"deep": -5.0, "cartoon": 7.0, "higher": 3.0, "cinematic": -2.0}[name]
            shifted = self._pitch_shift(pcm, steps)
            if name == "cinematic":
                cinematic_parameters = EffectParameters(
                    echo_delay_samples=int(0.14 * self.sample_rate),
                    echo_gain_q15=8_192,
                )
                shifted = self._cinematic_echo.process_block(
                    shifted, config.MODE_ECHO, cinematic_parameters
                )
            # Small boundary crossfade reduces clicks between independent blocks.
            fade = min(96, pcm.size // 4)
            if self._last_pitch_tail is not None and fade > 0:
                previous = self._last_pitch_tail[-fade:].astype(np.float32)
                current = shifted[:fade].astype(np.float32)
                ramp = np.linspace(0.0, 1.0, fade, endpoint=True, dtype=np.float32)
                shifted[:fade] = saturate_array_int16(previous * (1.0 - ramp) + current * ramp)
            self._last_pitch_tail = shifted.copy()
            return shifted
        raise ValueError(f"Unknown voice preset: {preset}")
