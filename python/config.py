"""Shared configuration for the Voice Modulator project."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
INPUT_AUDIO_DIR = DATA_DIR / "input_audio"
OUTPUT_AUDIO_DIR = DATA_DIR / "output_audio"
INPUT_SAMPLES_DIR = DATA_DIR / "input_samples"
OUTPUT_SAMPLES_DIR = DATA_DIR / "output_samples"
BUILD_DIR = PROJECT_ROOT / "build"

# Keep the initial Verilog-compatible path at 16 kHz mono PCM.
SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH_BITS = 16
BLOCK_SIZE = 2_048  # 128 ms at 16 kHz; gives the live worker more processing time.

# Verilog effect-mode encodings. Keep these synchronized with mode_selector.v.
MODE_BYPASS = 0
MODE_ROBOT = 1
MODE_ECHO = 2
MODE_RADIO = 3
MODE_VOLUME = 4

MODE_NAMES = {
    "normal": MODE_BYPASS,
    "robot": MODE_ROBOT,
    "echo": MODE_ECHO,
    "radio": MODE_RADIO,
    "volume": MODE_VOLUME,
}

# Defaults shared by Python fixed-point reference and Verilog simulation.
DEFAULT_RING_HALF_PERIOD = 100       # 80 Hz square carrier at 16 kHz sample rate
DEFAULT_ECHO_DELAY_SAMPLES = 3_200   # 200 ms at 16 kHz
DEFAULT_ECHO_GAIN_Q15 = 13_107      # approximately 0.4 in Q1.15
DEFAULT_VOLUME_LEVEL = 3            # 100%
ECHO_BUFFER_DEPTH = 4_096

# First-order high-pass + low-pass cascade coefficients for the radio effect.
# Q1.15 coefficients, calculated for the 16 kHz reference sample rate.
RADIO_ALPHA_HP_Q15 = 29_126
RADIO_ALPHA_LP_Q15 = 24_146

for directory in (INPUT_AUDIO_DIR, OUTPUT_AUDIO_DIR, INPUT_SAMPLES_DIR,
                  OUTPUT_SAMPLES_DIR, BUILD_DIR):
    directory.mkdir(parents=True, exist_ok=True)
