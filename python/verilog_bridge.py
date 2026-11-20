"""Run the Verilog DSP core in Icarus Verilog using signed PCM16 hex files."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
import numpy as np

from . import config
from .dsp_effects import EffectParameters
from .fixed_point import pcm16_to_hex, hex_to_pcm16
from .voice_presets import verilog_mode_for


class VerilogSimulationError(RuntimeError):
    pass


class VerilogBridge:
    def __init__(self, project_root: Path | None = None):
        self.project_root = Path(project_root or config.PROJECT_ROOT)
        self.build_dir = self.project_root / "build"
        self.input_dir = self.project_root / "data" / "input_samples"
        self.output_dir = self.project_root / "data" / "output_samples"
        self.simulator_path = self.build_dir / "voice_modulator.vvp"
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _tool(self, name: str) -> str:
        path = shutil.which(name)
        if not path:
            raise VerilogSimulationError(
                f"'{name}' was not found on PATH. Install Icarus Verilog and reopen "
                "the terminal. On Windows, ensure iverilog.exe and vvp.exe are on PATH."
            )
        return path

    def compile(self) -> Path:
        iverilog = self._tool("iverilog")
        sources = [
            "verilog/DesignCode.v",
            "testbench/tb_audio_file.v",
        ]
        command = [iverilog, "-g2012", "-Wall", "-o", str(self.simulator_path), *sources]
        result = subprocess.run(
            command, cwd=self.project_root, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            raise VerilogSimulationError(
                "Verilog compilation failed.\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        return self.simulator_path

    def process_samples(self, samples: np.ndarray, preset: str,
                        parameters: EffectParameters | None = None) -> np.ndarray:
        samples = np.asarray(samples, dtype=np.int16).reshape(-1)
        if samples.size == 0:
            return samples.copy()
        if samples.size > 2_000_000:
            raise ValueError(
                "This initial file-based simulation is limited to 2,000,000 samples "
                "per run. Split very long recordings into shorter files."
            )
        mode = verilog_mode_for(preset)
        p = parameters or EffectParameters()

        input_path = self.input_dir / "input_samples.hex"
        output_path = self.output_dir / "verilog_output.hex"
        input_path.write_text("\n".join(pcm16_to_hex(int(x)) for x in samples) + "\n", encoding="ascii")
        if output_path.exists():
            output_path.unlink()

        self.compile()
        vvp = self._tool("vvp")
        input_arg = input_path.relative_to(self.project_root).as_posix()
        output_arg = output_path.relative_to(self.project_root).as_posix()
        command = [
            vvp,
            self.simulator_path.relative_to(self.project_root).as_posix(),
            f"+INPUT={input_arg}",
            f"+OUTPUT={output_arg}",
            f"+NUM={samples.size}",
            f"+MODE={mode}",
            f"+VOLUME={int(p.volume_level)}",
            f"+ECHO_DELAY={int(p.echo_delay_samples)}",
            f"+ECHO_GAIN={int(p.echo_gain_q15)}",
            f"+RING_HALF={int(p.ring_half_period_samples)}",
        ]
        result = subprocess.run(
            command, cwd=self.project_root, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            raise VerilogSimulationError(
                "Verilog simulation failed.\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        if not output_path.exists():
            raise VerilogSimulationError(
                "The simulator did not create its output sample file.\n" + result.stdout
            )
        output = []
        for line_number, line in enumerate(output_path.read_text(encoding="ascii").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                output.append(hex_to_pcm16(line))
            except ValueError as exc:
                raise VerilogSimulationError(
                    f"Invalid output word on line {line_number}: {line!r}"
                ) from exc
        result_samples = np.asarray(output, dtype=np.int16)
        if result_samples.size != samples.size:
            raise VerilogSimulationError(
                f"Sample count mismatch: input={samples.size}, output={result_samples.size}. "
                f"Simulator output: {result.stdout.strip()}"
            )
        return result_samples
