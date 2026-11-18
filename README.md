# Programmable Voice Modulator — Python + Verilog HDL

A second-year engineering project demonstrating digital voice effects using a Python desktop application and a synthesizable Verilog DSP core.

## What is included

- **Python live microphone mode:** continuously captures audio and plays processed audio using SoundDevice.
- **Python WAV mode:** loads, processes, plays and saves recorded WAV audio.
- **Verilog simulation mode:** runs the actual Verilog modules in Icarus Verilog for recorded audio samples.
- **Verification:** compares Verilog results against a matching Python fixed-point reference.

> There is no FPGA integration in this version. Live microphone processing is performed by Python. Icarus Verilog processes recorded sample files in simulation; it is not used as a real-time microphone audio engine.

## Effects

| Preset | Python live | Python WAV | Verilog simulation |
|---|---:|---:|---:|
| Normal / Bypass | Yes | Yes | Yes |
| Robot / ring modulation | Yes | Yes | Yes |
| Echo | Yes | Yes | Yes |
| Radio / telephone filter | Yes | Yes | Yes |
| Volume control | Yes | Yes | Yes |
| Deep / Monster (pitch shift) | Experimental block processing | Yes | Not in initial HDL core |
| Cartoon / Chipmunk (pitch shift) | Experimental block processing | Yes | Not in initial HDL core |
| Higher / Brighter | Experimental block processing | Yes | Not in initial HDL core |
| Cinematic | Experimental block processing | Yes | Not in initial HDL core |

The Robot effect in the initial Verilog core uses a square-wave carrier (alternating +1/-1). It creates an intentionally buzzy/metallic effect. The Deep/Cartoon effects use Python pitch shifting. A simple playback-rate change changes both pitch and duration; Librosa's offline pitch-shift operation aims to preserve duration but is more computationally demanding.

## Audio and fixed-point settings

- Verilog-compatible sample rate: **16,000 Hz**
- Channels: **Mono**
- PCM format: **Signed 16-bit**
- Live block size: **2,048 samples** (128 ms at 16 kHz)
- Echo buffer: 4,096 samples
- Default echo: 200 ms, 40% gain
- Default Robot carrier: 80 Hz

WAV files with other sample rates or multiple channels are converted to 16 kHz mono for this initial project. The original source file is not modified.

## Project structure

```text
Voice_Modulator/
├── python/                 # GUI, audio I/O, Python DSP and Verilog bridge
├── verilog/                # Synthesizable DSP modules
├── testbench/              # File-driven Verilog testbench
├── scripts/                # Demo generation and simulation command
├── tests/                  # Python unit tests
├── data/
│   ├── input_audio/
│   ├── output_audio/
│   ├── input_samples/
│   └── output_samples/
├── build/                  # Icarus simulation executable
├── documentation/          # Architecture and implementation notes
└── README.md
```

## Windows installation

### 1. Install Python

Use Python 3.10 or newer. Python 3.11 is a suitable choice for this project.

### 2. Create a virtual environment

Open PowerShell or Command Prompt in the project folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r python\requirements.txt
```

If PowerShell blocks activation, use Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

### 3. Install Icarus Verilog

Install Icarus Verilog for Windows. Ensure that both `iverilog.exe` and `vvp.exe` are available on your system `PATH`. Close and reopen the terminal after changing `PATH`.

Check installation:

```powershell
iverilog -V
vvp -V
```

GTKWave is optional for future RTL waveform inspection. The current file-driven testbench does not produce a large VCD by default.

## Run the desktop application

From the project root, with the virtual environment active:

```powershell
python -m python.main
```

### Live microphone use

1. Connect a microphone and headphones/speakers.
2. Use **Refresh Audio Devices** and select the input/output devices (or leave the defaults).
3. Select a preset.
4. Click **Start Live Processing**.
5. Speak into the microphone.
6. Click **Stop Live Processing** when finished.

Live processing runs in Python. The GUI reports callback overflow/underflow, queue drops and the last worker-block processing time. These counters help diagnose dropouts, but a general-purpose Windows computer cannot provide an unconditional hard real-time guarantee.

The initial live pitch presets process blocks using Librosa and may add latency or block-boundary artifacts. The lightweight Robot, Echo, Radio and Volume presets are better starting choices for live demonstrations.

### Recorded WAV use

1. Click **Choose WAV File**.
2. Select a WAV recording.
3. Select a voice preset.
4. Choose **Python** or **Verilog Simulation** as the backend.
5. Click **Process WAV**.
6. Listen to the original or processed audio.
7. Use **Save Processed As...** to save another copy.

The Verilog Simulation backend supports Normal, Robot, Echo, Radio and Volume. Pitch-based presets are Python-only in this initial version.

## Run Python unit tests

From the project root:

```powershell
python -m unittest discover -s tests -v
```

## Generate a sample WAV

```powershell
python scripts\generate_demo_wav.py
```

This creates a short synthetic harmonic test tone in `data/input_audio/`. It is not a speech recording. You can use your own voice WAV file for a more meaningful demonstration.

## Run the Verilog simulation demo

After Icarus Verilog is installed and on `PATH`:

```powershell
python scripts\run_verilog_demo.py --preset robot --file data/input_audio/demo_voice_like_tone.wav
```

Other supported presets:

```powershell
python scripts\run_verilog_demo.py --preset normal
python scripts\run_verilog_demo.py --preset echo --echo-ms 200 --echo-percent 40
python scripts\run_verilog_demo.py --preset radio
python scripts\run_verilog_demo.py --preset volume --volume-level 2
```

Volume level codes:

- `0`: mute
- `1`: 25%
- `2`: 50%
- `3`: 100%
- `4`: 200% (saturating)

The script prints a sample-by-sample comparison report and saves the Verilog result under `data/output_audio/`.

## Verilog mode encoding

The mode values are defined in `verilog/mode_selector.v` and mirrored in `python/config.py`:

| Mode | Effect |
|---:|---|
| 0 | Bypass |
| 1 | Robot / square-carrier ring modulation |
| 2 | Echo |
| 3 | Radio filter |
| 4 | Volume control |

The Verilog core registers one output sample for each accepted input sample. Its output-valid signal is aligned with the registered effect outputs. The testbench samples outputs after the nonblocking assignments have updated.

## Fixed-point reference agreement

The Python reference in `python/dsp_effects.py` mirrors the Verilog behavior for the five shared effects. Both use:

- Signed PCM16 input/output.
- The same mode values.
- The same Q1.15 echo gain and filter coefficients.
- Arithmetic right shifts.
- Saturation to [-32768, 32767].
- A 4,096-sample circular echo buffer.
- The same ring-carrier half-period counter.

The Python/Verilog comparison should be exact sample by sample. If the comparison fails, inspect the compiler/simulation output and the first mismatched sample before using the result in a report.

## Important technical limitations

1. **No physical FPGA is included.** The current Verilog code is a simulation-ready DSP core. ADC/DAC and board-specific I2S interfaces are future work.
2. **Live microphone mode is Python-based.** Icarus Verilog is not a real-time audio streaming backend.
3. **Pitch shifting is not initially implemented in Verilog.** Deep/Cartoon/Higher/Cinematic pitch effects run through Python only.
4. **Robot effect is a square-carrier ring modulator.** It creates a simple electronic effect; a sine-table carrier would be a refinement.
5. **Radio filter is a simple first-order HP/LP cascade.** It is an educational approximation to a telephone-style band-pass response, not a high-order studio filter.
6. **Echo memory reset:** the simulation core clears its 4,096-word delay memory on reset. A physical FPGA implementation may need a RAM-initialization or valid-bit strategy to infer block RAM efficiently.
7. **Real-time reliability:** Python callback underruns/overruns depend on audio drivers, OS scheduling and CPU load. Monitor the status counters and use headphones to avoid acoustic feedback.
8. **Voice identity:** DSP presets alter pitch and spectral characteristics; they do not reproduce an actor's or character's exact voice.

## Suggested next FPGA stage

Once the software and simulation versions pass verification, the DSP core can be connected to a suitable FPGA board and audio codec. The future system would need an I2S receiver, input buffering, the DSP core, output buffering, an I2S transmitter, appropriate clocks and board-specific constraints. Choose the FPGA board and audio codec before creating pin assignments.
