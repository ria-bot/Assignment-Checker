import pyaudiowpatch as pyaudio

class AudioCapture:
    def __init__(self, samplerate=44100, blocksize=1024):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.buffer = np.zeros(blocksize, dtype=np.float32)
        self.lock = threading.Lock()
        self.stream = None
        self.p = None

    def _callback(self, in_data, frame_count, time_info, status):
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        if len(audio_data) > 0:
            mono = audio_data.reshape(-1, 2).mean(axis=1) if audio_data.ndim == 1 else audio_data
            with self.lock:
                self.buffer = mono[:self.blocksize] if len(mono) >= self.blocksize else np.pad(mono, (0, self.blocksize - len(mono)))
        return (in_data, pyaudio.paContinue)

    def start(self):
        self.p = pyaudio.PyAudio()
        
        # Find the default WASAPI loopback device
        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = self.p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            
            if not default_speakers["isLoopbackDevice"]:
                for loopback in self.p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        break
        except OSError:
            raise RuntimeError("WASAPI is not available on this system.")
        
        if not default_speakers["isLoopbackDevice"]:
            raise RuntimeError("Could not find a WASAPI loopback device.")

        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=default_speakers["maxInputChannels"],
            rate=int(default_speakers["defaultSampleRate"]),
            input=True,
            input_device_index=default_speakers["index"],
            frames_per_buffer=self.blocksize,
            stream_callback=self._callback
        )
        self.stream.start_stream()

    def read(self):
        with self.lock:
            return self.buffer.copy()

    def stop(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()