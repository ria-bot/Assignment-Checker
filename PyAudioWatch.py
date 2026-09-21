import threading

import numpy as np
import soundcard as sc

class AudioCapture:
    def __init__(self, samplerate=44100, blocksize=1024):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.buffer = np.zeros(blocksize, dtype=np.float32)
        self.lock = threading.Lock()
        self.recorder = None
        self._stop = threading.Event()
        self._thread = None

    def _record_loop(self):
        try:
            with self.recorder:
                while not self._stop.is_set():
                    audio_data = np.asarray(
                        self.recorder.record(self.blocksize), dtype=np.float32
                    )
                    if audio_data.ndim > 1:
                        audio_data = audio_data.mean(axis=1)
                    if len(audio_data) >= self.blocksize:
                        mono = audio_data[:self.blocksize]
                    else:
                        mono = np.pad(audio_data, (0, self.blocksize - len(audio_data)))
                    with self.lock:
                        self.buffer = mono
        except Exception as error:
            print(f"Audio capture stopped: {error}")

    def start(self):
        try:
            microphone = sc.default_speaker().get_microphone()
        except Exception as error:
            raise RuntimeError("Could not find the default speaker loopback device.") from error

        print(f"Using device: {microphone.name}")
        self._stop.clear()
        self.recorder = microphone.recorder(
            samplerate=self.samplerate, channels=2
        )
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def read(self):
        with self.lock:
            return self.buffer.copy()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)
        self.recorder = None