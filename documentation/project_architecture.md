# Project Architecture

## Purpose

The Voice Modulator accepts live microphone audio or a recorded WAV file and applies selected voice effects. Python provides the application, audio I/O, and advanced pitch effects. Verilog implements a fixed-point DSP core for a subset of effects.

## Operating paths

### Live microphone

Microphone -> operating-system audio input -> SoundDevice -> Python DSP worker -> SoundDevice output -> headphones/speakers.

This path is software-only in the current version.

### Python WAV

WAV -> mono/resample to 16 kHz -> signed PCM16 samples -> Python DSP -> output WAV.

### Verilog-simulated WAV

WAV -> signed PCM16 samples -> hexadecimal file -> Icarus Verilog testbench -> Verilog DSP core -> hexadecimal output -> Python WAV reconstruction.

## Shared Verilog modes

- 0: bypass
- 1: square-carrier ring modulation
- 2: echo
- 3: radio-style first-order high-pass/low-pass cascade
- 4: volume control

Deep, Cartoon, Higher and Cinematic presets use Python-only pitch processing in this first version.

## Sample interface

The DSP core accepts signed 16-bit mono PCM samples. `sample_valid` indicates that `sample_in` is a new sample. Every effect module registers one output per accepted sample; `out_valid` signals a valid registered output. The mode is delayed by one clock to align with the registered effect values.

## Fixed-point conventions

Echo gain and radio filter coefficients use Q1.15. Products are shifted arithmetically right by 15 bits. Outputs are saturated to signed PCM16. The Python reference mirrors these integer operations.
