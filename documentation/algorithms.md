# Algorithms and Verilog Mapping

## Robot: square-carrier ring modulation

The carrier alternates between +1 and -1. The Verilog counter toggles its sign every `ring_half_period_samples` accepted samples. The output is either the input sample or its negation, with saturation for the -32768 corner case. Python uses the same counter and saturation rule.

At sample rate Fs, the approximate carrier frequency is Fs/(2*half_period). At 16 kHz and half-period 100, the carrier is 80 Hz.

## Echo

`y[n] = sat16(x[n] + ((x[n-D] * gain_q15) >>> 15))`.

A 4,096-word circular buffer stores recent input samples. The delayed read index is `(write_pointer - delay_samples) modulo 4096`. Gain is a non-negative Q1.15 value. The result is saturated to signed 16-bit PCM.

## Radio filter

The radio effect is a first-order high-pass followed by a first-order low-pass:

`hp[n] = alpha_hp * (hp[n-1] + x[n] - x[n-1])`

`lp[n] = lp[n-1] + alpha_lp * (hp[n] - lp[n-1])`

The coefficients are Q1.15 constants chosen for the 16 kHz reference sample rate. This is an educational approximation to a voice-band filter.

## Volume

- 0: mute
- 1: arithmetic shift right by 2 (25%)
- 2: arithmetic shift right by 1 (50%)
- 3: unity gain
- 4: shift left by 1 (200%) with saturation

## Pitch presets

Python uses Librosa pitch shifting for Deep, Cartoon and Higher presets on complete WAV files. A simple playback-rate change changes both pitch and duration, so the implementation uses a pitch-shifting algorithm intended to preserve duration. In live mode, blockwise processing is experimental and may add latency or artifacts. Pitch shifting is not implemented in the initial Verilog core.
