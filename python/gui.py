"""Tkinter desktop application for the Voice Modulator project."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading

import numpy as np

from . import config
from .audio_io import load_wav, save_wav
from .dsp_effects import EffectParameters
from .file_processor import process_wav
from .fixed_point import int16_to_float
from .live_audio import LiveAudioEngine
from .voice_presets import PRESETS

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    Figure = None
    FigureCanvasTkAgg = None


PRESET_LABEL_TO_KEY = {preset.label: key for key, preset in PRESETS.items()}


class VoiceModulatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Programmable Voice Modulator")
        self.root.geometry("1120x800")
        self.root.minsize(920, 680)

        self.input_path: Path | None = None
        self.original_samples: np.ndarray | None = None
        self.processed_samples: np.ndarray | None = None
        self.processed_path: Path | None = None
        self.live_engine: LiveAudioEngine | None = None

        self.preset_var = tk.StringVar(value="Normal / Bypass")
        self.backend_var = tk.StringVar(value="Python")
        self.status_var = tk.StringVar(value="Ready")
        self.file_var = tk.StringVar(value="No WAV file selected")
        self.echo_ms_var = tk.IntVar(value=200)
        self.echo_percent_var = tk.IntVar(value=40)
        self.volume_level_var = tk.IntVar(value=3)
        self.volume_choice_var = tk.StringVar(value="100%")
        self.robot_hz_var = tk.IntVar(value=80)
        self.input_count_var = tk.StringVar(value="Input samples: —")
        self.output_count_var = tk.StringVar(value="Output samples: —")
        self.backend_note_var = tk.StringVar(value="Live microphone processing always uses the Python audio engine.")
        self.input_device_var = tk.StringVar(value="Default input")
        self.output_device_var = tk.StringVar(value="Default output")
        self.input_device_map: dict[str, int | None] = {"Default input": None}
        self.output_device_map: dict[str, int | None] = {"Default output": None}

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(500, self._refresh_status)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="VOICE MODULATOR", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Real-time voice effects with Python and Verilog simulation",
            font=("Segoe UI", 10),
        ).pack(anchor="w")

        controls = ttk.LabelFrame(outer, text="Voice effect and backend", padding=10)
        controls.pack(fill="x", pady=5)
        ttk.Label(controls, text="Voice preset:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        preset_values = [preset.label for preset in PRESETS.values()]
        self.preset_combo = ttk.Combobox(
            controls, textvariable=self.preset_var, values=preset_values,
            state="readonly", width=25
        )
        self.preset_combo.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_changed)

        ttk.Label(controls, text="WAV processing backend:").grid(row=0, column=2, sticky="w", padx=(20, 4), pady=4)
        backend_combo = ttk.Combobox(
            controls, textvariable=self.backend_var,
            values=["Python", "Verilog Simulation"], state="readonly", width=21
        )
        backend_combo.grid(row=0, column=3, sticky="w", padx=4, pady=4)
        backend_combo.bind("<<ComboboxSelected>>", self._on_backend_changed)
        ttk.Label(controls, textvariable=self.backend_note_var, foreground="#555555").grid(
            row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(2, 4)
        )

        params = ttk.LabelFrame(outer, text="Effect parameters", padding=10)
        params.pack(fill="x", pady=5)
        ttk.Label(params, text="Echo delay (ms):").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Scale(params, from_=50, to=250, orient="horizontal", variable=self.echo_ms_var,
                  command=lambda _v: self._update_parameters()).grid(row=0, column=1, sticky="ew", padx=4)
        self.echo_ms_label = ttk.Label(params, text="200")
        self.echo_ms_label.grid(row=0, column=2, sticky="w", padx=4)

        ttk.Label(params, text="Echo intensity (%):").grid(row=0, column=3, sticky="w", padx=(18, 4))
        ttk.Scale(params, from_=0, to=70, orient="horizontal", variable=self.echo_percent_var,
                  command=lambda _v: self._update_parameters()).grid(row=0, column=4, sticky="ew", padx=4)
        self.echo_percent_label = ttk.Label(params, text="40")
        self.echo_percent_label.grid(row=0, column=5, sticky="w", padx=4)

        ttk.Label(params, text="Volume level:").grid(row=1, column=0, sticky="w", padx=4, pady=6)
        volume_combo = ttk.Combobox(params, textvariable=self.volume_choice_var,
                                    values=["Mute", "25%", "50%", "100%", "200%"],
                                    state="readonly", width=10)
        volume_combo.grid(row=1, column=1, sticky="w", padx=4, pady=6)
        volume_combo.bind("<<ComboboxSelected>>", self._on_volume_changed)
        self.volume_combo = volume_combo

        ttk.Label(params, text="Robot carrier (Hz):").grid(row=1, column=3, sticky="w", padx=(18, 4), pady=6)
        ttk.Scale(params, from_=40, to=200, orient="horizontal", variable=self.robot_hz_var,
                  command=lambda _v: self._update_parameters()).grid(row=1, column=4, sticky="ew", padx=4, pady=6)
        self.robot_hz_label = ttk.Label(params, text="80")
        self.robot_hz_label.grid(row=1, column=5, sticky="w", padx=4, pady=6)
        params.columnconfigure(1, weight=1)
        params.columnconfigure(4, weight=1)

        action_frame = ttk.Frame(outer)
        action_frame.pack(fill="x", pady=6)
        live_box = ttk.LabelFrame(action_frame, text="Live microphone", padding=10)
        live_box.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ttk.Button(live_box, text="Start Live Processing", command=self.start_live).pack(fill="x", pady=3)
        ttk.Button(live_box, text="Stop Live Processing", command=self.stop_live).pack(fill="x", pady=3)
        ttk.Label(live_box, text="Input device:").pack(anchor="w", pady=(5, 0))
        self.input_device_combo = ttk.Combobox(live_box, textvariable=self.input_device_var,
                                               values=["Default input"], state="readonly")
        self.input_device_combo.pack(fill="x", pady=2)
        ttk.Label(live_box, text="Output device:").pack(anchor="w", pady=(5, 0))
        self.output_device_combo = ttk.Combobox(live_box, textvariable=self.output_device_var,
                                                values=["Default output"], state="readonly")
        self.output_device_combo.pack(fill="x", pady=2)
        ttk.Button(live_box, text="Refresh Audio Devices", command=self.refresh_audio_devices).pack(fill="x", pady=3)
        ttk.Label(live_box, text="Live effects use Python. Verilog simulation is for recorded files.",
                  wraplength=330).pack(anchor="w", pady=(5, 0))
        self.refresh_audio_devices()

        file_box = ttk.LabelFrame(action_frame, text="Recorded WAV file", padding=10)
        file_box.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ttk.Button(file_box, text="Choose WAV File", command=self.choose_file).grid(row=0, column=0, padx=3, pady=3, sticky="ew")
        ttk.Button(file_box, text="Process WAV", command=self.process_file).grid(row=0, column=1, padx=3, pady=3, sticky="ew")
        ttk.Button(file_box, text="Play Original", command=self.play_original).grid(row=1, column=0, padx=3, pady=3, sticky="ew")
        ttk.Button(file_box, text="Play Processed", command=self.play_processed).grid(row=1, column=1, padx=3, pady=3, sticky="ew")
        ttk.Button(file_box, text="Save Processed As...", command=self.save_processed_as).grid(row=2, column=0, columnspan=2, padx=3, pady=3, sticky="ew")
        ttk.Label(file_box, textvariable=self.file_var, wraplength=420).grid(row=3, column=0, columnspan=2, sticky="w", pady=4)
        file_box.columnconfigure(0, weight=1)
        file_box.columnconfigure(1, weight=1)

        status = ttk.LabelFrame(outer, text="System status", padding=8)
        status.pack(fill="x", pady=5)
        ttk.Label(status, textvariable=self.status_var).pack(anchor="w")
        ttk.Label(status, textvariable=self.input_count_var).pack(anchor="w")
        ttk.Label(status, textvariable=self.output_count_var).pack(anchor="w")

        graph_box = ttk.LabelFrame(outer, text="Audio analysis", padding=6)
        graph_box.pack(fill="both", expand=True, pady=5)
        if Figure is not None and FigureCanvasTkAgg is not None:
            self.figure = Figure(figsize=(8, 3.2), dpi=90)
            self.wave_ax = self.figure.add_subplot(211)
            self.spec_ax = self.figure.add_subplot(212)
            self.figure.tight_layout()
            self.canvas = FigureCanvasTkAgg(self.figure, master=graph_box)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            self._plot_empty()
        else:
            ttk.Label(graph_box, text="Install matplotlib to enable waveform and spectrum plots.").pack(pady=20)

    def _preset_key(self) -> str:
        return PRESET_LABEL_TO_KEY[self.preset_var.get()]

    def _parameters(self) -> EffectParameters:
        delay_samples = max(1, int(round(self.echo_ms_var.get() * config.SAMPLE_RATE / 1000.0)))
        gain_q15 = int(round(self.echo_percent_var.get() * 32768 / 100.0))
        gain_q15 = min(32767, max(0, gain_q15))
        half_period = max(1, int(round(config.SAMPLE_RATE / (2 * max(1, self.robot_hz_var.get())))))
        return EffectParameters(
            ring_half_period_samples=half_period,
            echo_delay_samples=min(delay_samples, config.ECHO_BUFFER_DEPTH - 1),
            echo_gain_q15=gain_q15,
            volume_level=int(self.volume_level_var.get()),
        )

    def _update_parameters(self) -> None:
        self.echo_ms_label.configure(text=str(self.echo_ms_var.get()))
        self.echo_percent_label.configure(text=str(self.echo_percent_var.get()))
        self.robot_hz_label.configure(text=str(self.robot_hz_var.get()))
        if self.live_engine is not None:
            self.live_engine.set_parameters(self._parameters())

    def _on_volume_changed(self, _event=None) -> None:
        mapping = {"Mute": 0, "25%": 1, "50%": 2, "100%": 3, "200%": 4}
        self.volume_level_var.set(mapping[self.volume_combo.get()])
        self._update_parameters()

    def _on_preset_changed(self, _event=None) -> None:
        if self.live_engine is not None:
            self.live_engine.set_preset(self._preset_key())
        self.status_var.set(f"Selected preset: {self.preset_var.get()}")

    def _on_backend_changed(self, _event=None) -> None:
        if self.backend_var.get() == "Verilog Simulation":
            self.backend_note_var.set("Verilog backend supports Normal, Robot, Echo, Radio and Volume presets.")
        else:
            self.backend_note_var.set("Python backend supports all listed presets, including pitch effects.")

    def choose_file(self) -> None:
        filename = filedialog.askopenfilename(
            title="Choose an audio file",
            filetypes=[("WAV audio", "*.wav"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            samples, _ = load_wav(filename, config.SAMPLE_RATE)
        except Exception as exc:
            messagebox.showerror("Could not open audio", str(exc))
            return
        self.input_path = Path(filename)
        self.original_samples = samples
        self.processed_samples = None
        self.processed_path = None
        self.file_var.set(f"{self.input_path.name} — {samples.size:,} mono samples at {config.SAMPLE_RATE} Hz")
        self.input_count_var.set(f"Input samples: {samples.size:,}")
        self.output_count_var.set("Output samples: —")
        self._plot_audio(self.original_samples, None)
        self.status_var.set("WAV file loaded and converted to 16 kHz mono PCM16.")

    def process_file(self) -> None:
        if self.input_path is None:
            messagebox.showinfo("Choose a file", "Choose a WAV file first.")
            return
        preset = self._preset_key()
        backend = self.backend_var.get()
        self.status_var.set("Processing WAV file...")
        self.root.update_idletasks()
        try:
            processed, saved = process_wav(
                self.input_path, preset, backend, self._parameters()
            )
        except Exception as exc:
            messagebox.showerror("Processing failed", str(exc))
            self.status_var.set("Processing failed.")
            return
        self.processed_samples = processed
        self.processed_path = saved
        self.output_count_var.set(f"Output samples: {processed.size:,}")
        self._plot_audio(self.original_samples, self.processed_samples)
        self.status_var.set(f"Completed using {backend}. Saved: {saved.name}")
        messagebox.showinfo("Processing complete", f"Processed audio saved to:\n{saved}")

    def play_original(self) -> None:
        if self.original_samples is None:
            messagebox.showinfo("No audio", "Choose a WAV file first.")
            return
        if sd is None:
            messagebox.showerror("Missing dependency", "Install sounddevice to play audio.")
            return
        try:
            sd.stop()
            sd.play(int16_to_float(self.original_samples), config.SAMPLE_RATE)
        except Exception as exc:
            messagebox.showerror("Playback failed", str(exc))

    def play_processed(self) -> None:
        if self.processed_samples is None:
            messagebox.showinfo("No processed audio", "Process a WAV file first.")
            return
        if sd is None:
            messagebox.showerror("Missing dependency", "Install sounddevice to play audio.")
            return
        try:
            sd.stop()
            sd.play(int16_to_float(self.processed_samples), config.SAMPLE_RATE)
        except Exception as exc:
            messagebox.showerror("Playback failed", str(exc))

    def save_processed_as(self) -> None:
        if self.processed_samples is None:
            messagebox.showinfo("No processed audio", "Process a WAV file first.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save processed audio",
            defaultextension=".wav",
            filetypes=[("WAV audio", "*.wav")],
            initialfile=f"{self.input_path.stem if self.input_path else 'voice'}_modified.wav",
        )
        if not filename:
            return
        try:
            save_wav(filename, self.processed_samples, config.SAMPLE_RATE)
            self.status_var.set(f"Saved processed audio: {filename}")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))


    def refresh_audio_devices(self) -> None:
        if sd is None:
            return
        try:
            devices = sd.query_devices()
            self.input_device_map = {"Default input": None}
            self.output_device_map = {"Default output": None}
            input_values = ["Default input"]
            output_values = ["Default output"]
            for index, device in enumerate(devices):
                name = str(device.get("name", f"Device {index}"))
                if int(device.get("max_input_channels", 0)) > 0:
                    label = f"{index}: {name}"
                    self.input_device_map[label] = index
                    input_values.append(label)
                if int(device.get("max_output_channels", 0)) > 0:
                    label = f"{index}: {name}"
                    self.output_device_map[label] = index
                    output_values.append(label)
            self.input_device_combo.configure(values=input_values)
            self.output_device_combo.configure(values=output_values)
            if self.input_device_var.get() not in self.input_device_map:
                self.input_device_var.set("Default input")
            if self.output_device_var.get() not in self.output_device_map:
                self.output_device_var.set("Default output")
        except Exception as exc:
            self.status_var.set(f"Could not enumerate audio devices: {exc}")

    def start_live(self) -> None:
        if self.live_engine is not None:
            return
        try:
            self.live_engine = LiveAudioEngine(
                sample_rate=config.SAMPLE_RATE,
                block_size=config.BLOCK_SIZE,
                input_device=self.input_device_map.get(self.input_device_var.get()),
                output_device=self.output_device_map.get(self.output_device_var.get()),
            )
            self.live_engine.set_preset(self._preset_key())
            self.live_engine.set_parameters(self._parameters())
            self.live_engine.start()
        except Exception as exc:
            self.live_engine = None
            messagebox.showerror("Could not start live audio", str(exc))
            self.status_var.set("Live audio could not start.")
            return
        self.status_var.set("Live microphone processing is running through Python.")

    def stop_live(self) -> None:
        if self.live_engine is not None:
            try:
                self.live_engine.stop()
            finally:
                self.live_engine = None
        if sd is not None:
            try:
                sd.stop()
            except Exception:
                pass
        self.status_var.set("Live processing stopped.")

    def _plot_empty(self) -> None:
        self.wave_ax.clear()
        self.spec_ax.clear()
        self.wave_ax.set_title("Audio waveform")
        self.spec_ax.set_title("Frequency spectrum")
        self.canvas.draw_idle()

    def _plot_audio(self, original: np.ndarray | None, processed: np.ndarray | None) -> None:
        if Figure is None or original is None:
            return
        self.wave_ax.clear()
        self.spec_ax.clear()
        count = min(len(original), config.SAMPLE_RATE * 2)
        time_axis = np.arange(count) / config.SAMPLE_RATE
        self.wave_ax.plot(time_axis, int16_to_float(original[:count]), label="Original", linewidth=0.8)
        if processed is not None:
            count_out = min(len(processed), config.SAMPLE_RATE * 2)
            self.wave_ax.plot(np.arange(count_out) / config.SAMPLE_RATE,
                              int16_to_float(processed[:count_out]), label="Processed", linewidth=0.8, alpha=0.8)
        self.wave_ax.set_title("Audio waveform (first 2 seconds)")
        self.wave_ax.set_xlabel("Time (s)")
        self.wave_ax.set_ylabel("Amplitude")
        self.wave_ax.grid(True, alpha=0.25)
        self.wave_ax.legend(loc="upper right")

        def add_spectrum(data: np.ndarray, label: str) -> None:
            data = int16_to_float(data)
            if data.size < 2:
                return
            segment = data[: min(data.size, 16_384)]
            window = np.hanning(segment.size)
            spectrum = np.abs(np.fft.rfft(segment * window))
            frequencies = np.fft.rfftfreq(segment.size, 1.0 / config.SAMPLE_RATE)
            spectrum_db = 20 * np.log10(np.maximum(spectrum, 1e-8))
            self.spec_ax.plot(frequencies, spectrum_db, label=label, linewidth=0.8)

        add_spectrum(original, "Original")
        if processed is not None:
            add_spectrum(processed, "Processed")
        self.spec_ax.set_title("Frequency spectrum (software FFT analysis)")
        self.spec_ax.set_xlabel("Frequency (Hz)")
        self.spec_ax.set_ylabel("Magnitude (dB, relative)")
        self.spec_ax.grid(True, alpha=0.25)
        self.spec_ax.legend(loc="upper right")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _refresh_status(self) -> None:
        if self.live_engine is not None:
            status = self.live_engine.get_status()
            self.status_var.set(
                "LIVE | preset={preset} | blocks={processed_blocks} | "
                "input overflow={input_overflow_callbacks} | output underflow={output_underflow_callbacks} | "
                "queue drops={input_queue_drops}/{output_queue_drops} | last block={last_processing_ms:.1f} ms".format(**status)
            )
            if status.get("last_error"):
                self.status_var.set(self.status_var.get() + f" | error: {status['last_error']}")
        self.root.after(500, self._refresh_status)

    def _on_close(self) -> None:
        self.stop_live()
        self.root.destroy()


def launch_gui() -> None:
    root = tk.Tk()
    VoiceModulatorApp(root)
    root.mainloop()
