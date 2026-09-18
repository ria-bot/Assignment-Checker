import os
import math
import threading
import asyncio
import tkinter as tk
import colorsys

import numpy as np
import pyaudiowpatch as pyaudio
from pycaw.pycaw import AudioUtilities

from PIL import Image, ImageDraw
import pystray

# winrt media control
try:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )
    WINRT_OK = True
except Exception:
    WINRT_OK = False

# ---------- Config ----------
WINDOW_SIZE = 280
RECORD_RADIUS = 90
RIPPLE_MAX = 130
FPS = 60
NUM_BARS = 72
SMOOTHING = 0.35
BASS_BOOST = 1.6
BG_COLOR = "#AB6422"


# ---------- Device picker ----------
def pick_loopback_device(p):
    loopbacks = list(p.get_loopback_device_info_generator())
    if not loopbacks:
        return None

    chosen = {"index": None}

    dlg = tk.Tk()
    dlg.title("Choose audio output to visualize")
    dlg.configure(bg="#1A1A1A")
    dlg.geometry("440x" + str(140 + 44 * len(loopbacks)))
    dlg.attributes("-topmost", True)

    tk.Label(
        dlg, text="Which output should I listen to?",
        bg="#1A1A1A", fg="#EAEAEA",
        font=("Segoe UI", 11, "bold")
    ).pack(anchor="w", padx=16, pady=(14, 4))

    tk.Label(
        dlg, text="Pick the one your music is actually playing through.",
        bg="#1A1A1A", fg="#888",
        font=("Segoe UI", 9)
    ).pack(anchor="w", padx=16, pady=(0, 10))

    def make_picker(info):
        def on_pick():
            chosen["index"] = info["index"]
            dlg.destroy()

        name = info["name"].replace(" [Loopback]", "")
        btn = tk.Label(
            dlg, text=f"▶  {name}",
            bg="#2A2A2A", fg="#EAEAEA",
            font=("Segoe UI", 10),
            anchor="w", padx=12, pady=8,
            cursor="hand2"
        )
        btn.pack(fill="x", padx=16, pady=3)

        btn.bind("<Enter>", lambda e: btn.configure(bg="#3A3A6A"))
        btn.bind("<Leave>", lambda e: btn.configure(bg="#2A2A2A"))
        btn.bind("<Button-1>", lambda e: on_pick())

    for info in loopbacks:
        make_picker(info)

    dlg.mainloop()
    return chosen["index"]


# ---------- Audio capture ----------
class AudioCapture:
    def __init__(self, blocksize=1024):
        self.blocksize = blocksize
        self.buffer = np.zeros(blocksize, dtype=np.float32)
        self.lock = threading.Lock()
        self.stream = None
        self.p = None

    def _callback(self, in_data, frame_count, time_info, status):
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        if audio_data.size > 0:
            if audio_data.ndim == 1 and audio_data.size % 2 == 0:
                mono = audio_data.reshape(-1, 2).mean(axis=1)
            else:
                mono = audio_data
            if len(mono) >= self.blocksize:
                mono = mono[:self.blocksize]
            else:
                mono = np.pad(mono, (0, self.blocksize - len(mono)))
            with self.lock:
                self.buffer = mono
        return (in_data, pyaudio.paContinue)

    def start(self, device_index):
        self.p = pyaudio.PyAudio()
        info = self.p.get_device_info_by_index(device_index)
        print(f"Using device: {info['name']}")

        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=info["maxInputChannels"],
            rate=int(info["defaultSampleRate"]),
            input=True,
            input_device_index=info["index"],
            frames_per_buffer=self.blocksize,
            stream_callback=self._callback,
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


# ---------- FFT helpers ----------
def compute_bars(samples, num_bars=NUM_BARS):
    if len(samples) < 64:
        return np.zeros(num_bars)
    windowed = samples * np.hanning(len(samples))
    fft = np.abs(np.fft.rfft(windowed))
    fft = fft[1:]
    bands = np.array_split(fft, num_bars)
    bars = np.array([b.mean() for b in bands])
    peak = bars.max() if bars.max() > 0 else 1.0
    bars = bars / peak
    bars = np.power(bars, 0.5)
    return bars


def bass_level(samples):
    if len(samples) < 64:
        return 0.0
    fft = np.abs(np.fft.rfft(samples))
    bass_band = fft[1:40]
    level = bass_band.mean() * BASS_BOOST
    return float(min(level / 15.0, 1.0))


# ---------- Now playing via winrt ----------
class NowPlaying:
    def __init__(self):
        self.title = ""
        self.artist = ""
        self.is_playing = False
        self._stop = False

    async def _poll_loop(self):
        while not self._stop:
            try:
                manager = await MediaManager.request_async()
                session = manager.get_current_session()
                if session:
                    info = await session.try_get_media_properties_async()
                    self.title = info.title or ""
                    self.artist = info.artist or ""
                    playback = session.get_playback_info()
                    self.is_playing = playback.playback_status == PlaybackStatus.PLAYING
                else:
                    self.title = ""
                    self.artist = ""
                    self.is_playing = False
            except Exception:
                pass
            await asyncio.sleep(1.5)

    def start(self):
        def runner():
            asyncio.run(self._poll_loop())
        threading.Thread(target=runner, daemon=True).start()

    def stop(self):
        self._stop = True


# ---------- Main window ----------
class VinylWindow:
    def __init__(self, device_index):
        self.root = tk.Tk()
        self.root.title("Vinyl")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG_COLOR)
        self.root.withdraw()  # start hidden

        screen_w = self.root.winfo_screenwidth()
        self.root.geometry(
            f"{WINDOW_SIZE}x{WINDOW_SIZE}+{screen_w - WINDOW_SIZE - 40}+80"
        )

        self.canvas = tk.Canvas(
            self.root,
            width=WINDOW_SIZE,
            height=WINDOW_SIZE,
            bg=BG_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack()

        self.canvas.bind("<Button-1>", self._start_move)
        self.canvas.bind("<B1-Motion>", self._do_move)

        close_btn = tk.Label(
            self.canvas, text="✕", bg=BG_COLOR, fg="#FFFFFF",
            font=("Segoe UI", 11, "bold"), cursor="hand2"
        )
        close_btn.place(x=WINDOW_SIZE - 24, y=4)
        close_btn.bind("<Button-1>", lambda e: self._on_close())

        self.audio = AudioCapture()
        self.audio.start(device_index)

        self.now_playing = NowPlaying()
        if WINRT_OK:
            self.now_playing.start()

        self.rotation = 0.0
        self.smoothed = np.zeros(NUM_BARS)
        self.bass = 0.0

        self._tick()

    def _on_close(self):
        try:
            self.audio.stop()
        except Exception:
            pass
        try:
            self.now_playing.stop()
        except Exception:
            pass
        self.root.destroy()

    def show(self):
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.lift()

    def hide(self):
        self.root.withdraw()

    def toggle(self):
        if self.root.state() == "withdrawn":
            self.show()
        else:
            self.hide()

    def _start_move(self, e):
        self.root.x = e.x
        self.root.y = e.y

    def _do_move(self, e):
        x = e.x_root - self.root.x
        y = e.y_root - self.root.y
        self.root.geometry(f"+{x}+{y}")

    def _hsv_to_hex(self, h, s, v):
        r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    def _dot_color(self, angle_frac, bass):
        hue = angle_frac + self.rotation / 360.0 + bass * 0.15
        sat = 0.55 + bass * 0.45
        val = 0.7 + bass * 0.3
        return self._hsv_to_hex(hue, sat, val)

    def _tick(self):
        samples = self.audio.read()
        bars = compute_bars(samples, NUM_BARS)
        self.smoothed = SMOOTHING * self.smoothed + (1 - SMOOTHING) * bars
        self.bass = 0.7 * self.bass + 0.3 * bass_level(samples)

        playing = self.bass > 0.002 or self.now_playing.is_playing
        if playing:
            self.rotation += 0.9
            if self.rotation >= 360:
                self.rotation -= 360

        self._draw(playing)
        self.root.after(int(1000 / FPS), self._tick)

    def _draw(self, playing):
        c = self.canvas
        c.delete("all")

        cx, cy = WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 20

        # --- Ripple dots around the record ---
        for i in range(NUM_BARS):
            angle = (i / NUM_BARS) * 2 * math.pi - math.pi / 2
            amp = self.smoothed[i]
            r_outer = RECORD_RADIUS + 4 + amp * (RIPPLE_MAX - RECORD_RADIUS)
            x = cx + math.cos(angle) * r_outer
            y = cy + math.sin(angle) * r_outer
            size = 1.5 + amp * 3.5
            dot_color = self._dot_color(i / NUM_BARS, self.bass)
            c.create_oval(
                x - size, y - size, x + size, y + size,
                fill=dot_color, outline=""
            )

        # --- Black vinyl record ---
        c.create_oval(
            cx - RECORD_RADIUS, cy - RECORD_RADIUS,
            cx + RECORD_RADIUS, cy + RECORD_RADIUS,
            fill="#000000", outline="#111", width=2
        )

        # --- White grooves ---
        for r in range(20, RECORD_RADIUS - 18, 4):
            c.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline="#FFFFFF", width=1
            )

        # --- Rotating rainbow shine line ---
        hue = (self.rotation / 360.0 + self.bass * 0.2) % 1.0
        r_c, g_c, b_c = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
        shine_color = f"#{int(r_c * 255):02x}{int(g_c * 255):02x}{int(b_c * 255):02x}"

        shine_angle = math.radians(self.rotation)
        x2 = cx + math.cos(shine_angle) * (RECORD_RADIUS - 20)
        y2 = cy + math.sin(shine_angle) * (RECORD_RADIUS - 20)
        c.create_line(cx, cy, x2, y2, fill=shine_color, width=3)

        # --- Center label ---
        label_r = 26
        c.create_oval(
            cx - label_r, cy - label_r, cx + label_r, cy + label_r,
            fill="#000000", outline="#FFFFFF", width=2
        )
        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="#FFFFFF", outline="")

        # --- Now playing text ---
        title = self.now_playing.title or ("♪ Playing" if playing else "♪ Silent")
        artist = self.now_playing.artist
        c.create_text(
            cx, WINDOW_SIZE - 30,
            text=title[:32], fill="#FFFFFF",
            font=("Segoe UI", 9, "bold"), anchor="center"
        )
        if artist:
            c.create_text(
                cx, WINDOW_SIZE - 14,
                text=artist[:36], fill="#F0E0D0",
                font=("Segoe UI", 8), anchor="center"
            )

    def run(self):
        self.root.mainloop()


# ---------- Tray icon ----------
def make_tray_icon():
    img = Image.new("RGB", (64, 64), BG_COLOR)
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill="#000000", outline="#FFFFFF", width=2)
    d.ellipse((28, 28, 36, 36), fill="#FFFFFF")
    return img


def main():
    REALTEK_LOOPBACK_INDEX = 14
    win = VinylWindow(device_index=REALTEK_LOOPBACK_INDEX)

    def on_toggle(icon, item):
        win.root.after(0, win.toggle)

    def on_show(icon, item):
        win.root.after(0, win.show)

    def on_hide(icon, item):
        win.root.after(0, win.hide)

    def on_change_device(icon, item):
        def switch():
            try:
                win.audio.stop()
            except Exception:
                pass
            p_temp = pyaudio.PyAudio()
            chosen = pick_loopback_device(p_temp)
            p_temp.terminate()
            if chosen is None:
                return
            win.audio = AudioCapture()
            win.audio.start(chosen)
        win.root.after(0, switch)

    def on_quit(icon, item):
        icon.stop()
        win.root.after(0, win._on_close)

    menu = pystray.Menu(
        pystray.MenuItem("Show / Hide", on_toggle, default=True),
        pystray.MenuItem("Show", on_show),
        pystray.MenuItem("Hide", on_hide),
        pystray.MenuItem("Change device", on_change_device),
        pystray.MenuItem("Quit", on_quit),
    )
    icon = pystray.Icon("vinyl", make_tray_icon(), "Vinyl Visualizer", menu)
    win.tray_icon = icon

    threading.Thread(target=icon.run, daemon=True).start()
    win.run()


if __name__ == "__main__":
    main()