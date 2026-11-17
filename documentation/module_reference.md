# Module Reference

## Python modules

- `config.py`: paths, audio settings, mode encodings and default fixed-point parameters.
- `fixed_point.py`: signed PCM16 conversion, saturation and hexadecimal sample conversion.
- `dsp_effects.py`: deterministic Python reference model for the five Verilog effects plus Python pitch presets.
- `audio_io.py`: WAV loading, stereo-to-mono conversion, resampling and saving.
- `file_processor.py`: selects Python or Verilog simulation for recorded WAV processing.
- `live_audio.py`: SoundDevice duplex stream, callback queues and worker-thread processing.
- `verilog_bridge.py`: writes hex samples, compiles the HDL, invokes VVP and reads simulated output.
- `verification.py`: compares Python reference samples with Verilog output.
- `voice_presets.py`: available effect names and Verilog compatibility.
- `gui.py`: Tkinter interface.
- `main.py`: application entry point.

## Verilog modules

- `bypass.v`: one-cycle registered pass-through.
- `ring_modulator.v`: square-carrier polarity modulation with configurable half-period.
- `echo_unit.v`: 4,096-sample circular delay memory and Q1.15 echo gain.
- `radio_filter.v`: first-order high-pass then low-pass filter, using Q1.15 coefficients.
- `volume_control.v`: mute, 25%, 50%, unity and saturating 200% volume.
- `mode_selector.v`: combinational selection between registered effect paths.
- `voice_dsp_core.v`: instantiates effect modules and aligns mode with registered outputs.
- `top_module.v`: board-independent top-level wrapper.
- `tb_audio_file.v`: file-driven testbench for recorded audio samples.
