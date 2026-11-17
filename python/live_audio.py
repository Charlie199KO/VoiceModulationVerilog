"""Buffered live microphone-to-speaker processing using SoundDevice.

The audio callback only moves fixed-size blocks between queues. DSP work is
performed on a worker thread so plotting and heavier pitch effects do not run
inside the PortAudio callback.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Any

import numpy as np

from . import config
from .dsp_effects import PythonVoiceProcessor, EffectParameters


class LiveAudioEngine:
    def __init__(self, sample_rate: int = config.SAMPLE_RATE,
                 block_size: int = config.BLOCK_SIZE,
                 input_device: int | None = None,
                 output_device: int | None = None):
        self.sample_rate = int(sample_rate)
        self.block_size = int(block_size)
        self.input_device = input_device
        self.output_device = output_device
        self.preset = "normal"
        self.parameters = EffectParameters()
        self.processor = PythonVoiceProcessor(self.sample_rate)
        self._input_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=16)
        self._output_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=16)
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._stream: Any = None
        self._lock = threading.Lock()
        self.counters = {
            "input_overflow_callbacks": 0,
            "output_underflow_callbacks": 0,
            "input_queue_drops": 0,
            "output_queue_drops": 0,
            "processing_errors": 0,
            "processed_blocks": 0,
            "processed_samples": 0,
            "last_processing_ms": 0.0,
        }
        self.last_error: str | None = None

    @staticmethod
    def list_devices() -> list[dict]:
        try:
            import sounddevice as sd
            return sd.query_devices()
        except Exception:
            return []

    def set_preset(self, preset: str) -> None:
        self.preset = preset.strip().lower()

    def set_parameters(self, parameters: EffectParameters) -> None:
        self.parameters = parameters

    def _callback(self, indata, outdata, frames, time_info, status) -> None:
        if status:
            with self._lock:
                if getattr(status, "input_overflow", False):
                    self.counters["input_overflow_callbacks"] += 1
                if getattr(status, "output_underflow", False):
                    self.counters["output_underflow_callbacks"] += 1
        block = np.asarray(indata[:, 0], dtype=np.int16).copy()
        try:
            self._input_queue.put_nowait(block)
        except queue.Full:
            with self._lock:
                self.counters["input_queue_drops"] += 1

        try:
            output = self._output_queue.get_nowait()
            if output.size != frames:
                fitted = np.zeros(frames, dtype=np.int16)
                copied = min(frames, output.size)
                fitted[:copied] = output[:copied]
                output = fitted
                with self._lock:
                    self.counters["output_underflow_callbacks"] += 1
            outdata[:, 0] = output
        except queue.Empty:
            outdata.fill(0)
            with self._lock:
                self.counters["output_underflow_callbacks"] += 1

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                block = self._input_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            started = time.perf_counter()
            try:
                processed = self.processor.process_live_block(
                    block, self.preset, self.parameters
                )
                processed = np.asarray(processed, dtype=np.int16).reshape(-1)
                if processed.size != block.size:
                    fitted = np.zeros(block.size, dtype=np.int16)
                    copied = min(block.size, processed.size)
                    fitted[:copied] = processed[:copied]
                    processed = fitted
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                try:
                    self._output_queue.put(processed, timeout=0.25)
                except queue.Full:
                    with self._lock:
                        self.counters["output_queue_drops"] += 1
                with self._lock:
                    self.counters["processed_blocks"] += 1
                    self.counters["processed_samples"] += int(block.size)
                    self.counters["last_processing_ms"] = elapsed_ms
            except Exception as exc:
                self.last_error = str(exc)
                with self._lock:
                    self.counters["processing_errors"] += 1
                # Keep the stream alive and provide silence for a failed block.
                try:
                    self._output_queue.put(np.zeros(block.size, dtype=np.int16), timeout=0.1)
                except queue.Full:
                    pass

    def start(self) -> None:
        if self._stream is not None:
            return
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "Live audio requires sounddevice. Install it with: "
                "python -m pip install sounddevice"
            ) from exc

        self._stop_event.clear()
        self.processor.reset()
        # Warm up Librosa before starting the audio callback when a pitch-based
        # preset is selected. This avoids its first-import/JIT cost inside the
        # live processing interval. The result is intentionally discarded.
        if self.preset in {"deep", "cartoon", "higher", "cinematic"}:
            self.processor.process_live_block(
                np.zeros(self.block_size, dtype=np.int16), self.preset, self.parameters
            )
            self.processor.reset()
        self._input_queue = queue.Queue(maxsize=16)
        self._output_queue = queue.Queue(maxsize=16)
        # Two silent blocks establish a fixed startup buffer and avoid an
        # immediate output underflow while the worker starts.
        for _ in range(2):
            self._output_queue.put_nowait(np.zeros(self.block_size, dtype=np.int16))
        self._worker = threading.Thread(target=self._worker_loop, daemon=True,
                                        name="VoiceModulatorDSPWorker")
        self._worker.start()
        try:
            self._stream = sd.Stream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=1,
                dtype="int16",
                callback=self._callback,
                device=(self.input_device, self.output_device),
                latency="low",
            )
            self._stream.start()
        except Exception:
            self._stop_event.set()
            if self._worker:
                self._worker.join(timeout=1.0)
            self._worker = None
            self._stream = None
            raise

    def stop(self) -> None:
        self._stop_event.set()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
        if self._worker is not None:
            self._worker.join(timeout=2.0)
            self._worker = None

    def get_status(self) -> dict:
        with self._lock:
            status = dict(self.counters)
        status.update({
            "running": self._stream is not None,
            "input_queue_blocks": self._input_queue.qsize(),
            "output_queue_blocks": self._output_queue.qsize(),
            "preset": self.preset,
            "last_error": self.last_error,
        })
        return status
