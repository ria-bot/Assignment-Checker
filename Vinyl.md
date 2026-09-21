# Vinyl Player

A desktop music visualizer styled as a spinning vinyl record. It listens to system audio from Spotify, YouTube, Teams, or other apps, then draws circular sound waves that react in real time. The title and artist of the playing track appear beneath the record when Windows supplies them.

It lives in the system tray until you open it.

---

## What It Does

- Captures system audio through WASAPI loopback; no microphone or cables are needed.
- Spins the record while music plays and stops it when playback pauses.
- Pulses circular ripples outward on bass hits with colors around the ring.
- Rotates a rainbow shine line over the record.
- Reads the current track title and artist from the Windows media session.
- Provides tray actions to show, hide, quit, or switch the audio device.

---

## Requirements

### Software

- Windows 10/11, Linux, or macOS
- Python 3.10 or newer
- Visual Studio Code (optional)

Linux audio capture requires a PulseAudio-compatible server. PipeWire systems
usually provide this through the PipeWire PulseAudio compatibility layer.

### Hardware

Any laptop or desktop with working speakers or headphones.

No accounts are required.

---

## Install Libraries

Open a terminal and install the Python libraries:

```bash
python -m pip install numpy
python -m pip install soundcard pystray pillow
```

On Linux, install Tkinter and the PulseAudio runtime if they are not already
present. For Debian or Ubuntu:

```bash
sudo apt install python3-tk libpulse0
```

On Windows, the optional now-playing metadata support additionally uses:

```powershell
python -m pip install winrt-Windows.Media.Control
python -m pip install winrt-Windows.Foundation
python -m pip install winrt-Windows.Foundation.Collections
```

| Library | Purpose |
|---|---|
| `numpy` | Performs FFT calculations on audio samples. |
| `soundcard` | Captures speaker output through loopback on Windows, Linux, and macOS. |
| `pystray` and `pillow` | Create the system tray icon. |
| `winrt-Windows.*` | Optionally reads now-playing title and artist on Windows. |

The visualizer still works without WinRT, but the track title and artist will
not be shown. Do not install the deprecated `winsdk` package.

---

## Find Your Loopback Device

Audio output devices, including speakers, headphones, and HDMI monitors, expose
a loopback device the visualizer can monitor. The app displays available
loopback devices when it starts; choose the output where music is playing.

On Linux, you can inspect available PulseAudio/PipeWire devices with:

```bash
pactl list short sources
```

Look for a monitor source, such as:

```text
alsa_output.pci-0000_00_1f.3.analog-stereo.monitor
```

The exact name varies by system. You may need to choose a different device
after plugging in headphones or switching to monitor speakers.

---

## Configure the Device

No device index needs to be edited in `vinyl.py`. Select the active output in
the picker shown at startup, or use **Change device** in the tray menu.

---

## Folder Layout

```text
Assignment Checker/
|-- vinyl.py
|-- Vinyl.md
`-- requirements.txt
```

No accounts, tokens, or configuration files are needed beyond the audio device index in `vinyl.py`.

---

## Run the App

### From VS Code

Open a terminal in the project folder and run:

```bash
python vinyl.py
```

An orange tray icon with a black record appears. Left-click it to show the visualizer; right-click and choose **Quit** to stop it.

### At Login with Task Scheduler

1. Open **Task Scheduler** and select **Create Task**.
2. On **General**, name it `Vinyl Player` and choose **Run only when user is logged on**.
3. On **Triggers**, create an **At log on** trigger.
4. On **Actions**, add a **Start a program** action.
5. Set **Program/script** to your full `python.exe` path. Find it with `where.exe python`.
6. Set **Add arguments** to `vinyl.py` and **Start in** to the project-folder path.
7. On **Conditions**, clear **Start the task only if the computer is on AC power**.

### Without a Console Window

Create `launch_vinyl.vbs` in the project folder, adjusting paths as required:

```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\Users\glori\AppData\Local\Programs\Python\Python313\pythonw.exe"" ""C:\Users\glori\OneDrive\Documents\GitHub\Assignment Checker\vinyl.py""", 0, False
```

In Task Scheduler, run `wscript.exe` with the VBS file path as its argument. `pythonw.exe` runs without a console window.

---

## Using the Visualizer

### Tray Icon

- Left-click: show or hide the visualizer.
- Right-click: show, hide, change device, or quit.

### Window

- Drag anywhere to reposition it.
- Use the close button to hide it while audio monitoring continues.

The display includes a black vinyl record with grooves, bass-reactive ripple dots, a rotating rainbow shine line, and track title and artist text.

### Change Audio Device

If you switch output devices and the visualizer becomes silent, right-click the tray icon, choose **Change device**, and choose the new loopback output. The stream then restarts on that device.

---

## Customize the Look

Visual settings are near the top of `vinyl.py`:

```python
WINDOW_SIZE = 280
RECORD_RADIUS = 90
RIPPLE_MAX = 130
FPS = 60
NUM_BARS = 72
SMOOTHING = 0.35
BASS_BOOST = 1.6
BG_COLOR = "#AB6422"
```

Change `BG_COLOR` to adjust the background, for example `#1A1A1A` for dark gray or `#0A0A0A` for near-black.

To change record speed, adjust this line in `_tick()`:

```python
self.rotation += 0.9
```

Use a higher number for a faster spin or a lower one for a slower spin. To make ripples more responsive at low volume, reduce the divisor in `bass_level`:

```python
return float(min(level / 15.0, 1.0))
```

For example, use `10.0` for more sensitivity or `20.0` for less.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: soundcard` | Run `python -m pip install soundcard`. |
| `ModuleNotFoundError: tkinter` | Install the OS Tkinter package, for example `sudo apt install python3-tk` on Debian/Ubuntu. |
| No loopback device | Check that PulseAudio or PipeWire is running and that a monitor source exists. |
| Visualizer does not react to music | Use the loopback index for the active audio output. |
| Ripples barely move | Increase sensitivity in `bass_level` as described above. |
| No track title | Some playback apps do not provide a Windows media session; try Spotify desktop or focus the browser tab playing media. |
| Black corners | The window uses a solid background intentionally. |
| Tray icon is missing | Check the hidden-icons arrow (`^`) beside the Windows clock. |
| Two tray icons | Quit both instances and start the program once. |

---

## Privacy and Security

The application listens only to your computer's audio output. It does not access the microphone, connect to an external service, transmit data, or store recordings. Current-track metadata is read locally from Windows.

---

## Credits

- [SoundCard](https://github.com/bastibe/SoundCard)
- [pywinrt](https://github.com/pywinrt/pywinrt)
- [numpy](https://numpy.org/)
- [pystray](https://github.com/moses-palmer/pystray)

## License

Personal use. Modify freely.
