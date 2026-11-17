"""Voice preset metadata and Verilog compatibility mapping."""
from dataclasses import dataclass
from . import config


@dataclass(frozen=True)
class VoicePreset:
    key: str
    label: str
    description: str
    backend: str
    verilog_mode: int | None
    pitch_semitones: float = 0.0


PRESETS = {
    "normal": VoicePreset("normal", "Normal / Bypass", "Original voice without modification.", "both", config.MODE_BYPASS),
    "robot": VoicePreset("robot", "Robot", "Square-carrier ring modulation for an electronic voice.", "both", config.MODE_ROBOT),
    "echo": VoicePreset("echo", "Echo", "Adds a delayed and quieter copy of the voice.", "both", config.MODE_ECHO),
    "radio": VoicePreset("radio", "Radio / Telephone", "Restricts the voice to a telephone-like frequency band.", "both", config.MODE_RADIO),
    "volume": VoicePreset("volume", "Volume Control", "Applies a selectable amplitude gain.", "both", config.MODE_VOLUME),
    "deep": VoicePreset("deep", "Deep / Monster", "Lowers pitch; Python-only in this initial version.", "python", None, -5.0),
    "cartoon": VoicePreset("cartoon", "Cartoon / Chipmunk", "Raises pitch; Python-only in this initial version.", "python", None, 7.0),
    "higher": VoicePreset("higher", "Higher / Brighter", "A stylized higher-pitched voice; Python-only initially.", "python", None, 3.0),
    "cinematic": VoicePreset("cinematic", "Cinematic Narrator", "Slightly lowers pitch and adds a subtle echo; Python-only initially.", "python", None, -2.0),
}


def get_preset(key: str) -> VoicePreset:
    try:
        return PRESETS[key.strip().lower()]
    except KeyError as exc:
        raise ValueError(f"Unknown preset: {key}") from exc


def verilog_mode_for(key: str) -> int:
    preset = get_preset(key)
    if preset.verilog_mode is None:
        raise ValueError(
            f"{preset.label} is Python-only in the initial version. "
            "Choose Normal, Robot, Echo, Radio or Volume for Verilog simulation."
        )
    return preset.verilog_mode
