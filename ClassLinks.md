# Class Links

A small always-on-top note that lists Microsoft Teams classes as clickable buttons. Choose a class and Teams opens its meeting, without looking through the calendar or manually entering meeting details.

It stays in the system tray until needed.

---

## What It Does

- Reads one class per line from `teams_codes.txt`.
- Shows classes as clickable buttons in a compact window.
- Opens meetings through the `msteams://` protocol, with a browser fallback.
- Hides after a class is opened.
- Provides tray actions to show, hide, reload, or quit.
- Reloads changed codes without restarting.

---

## Requirements

### Software

- Windows 10 or 11
- Python 3.10 or newer
- Microsoft Teams desktop application
- Visual Studio Code (optional)

Install the required libraries from PowerShell:

```powershell
python -m pip install pystray pillow
```

| Library | Purpose |
|---|---|
| `pystray` | Creates the system tray icon. |
| `pillow` | Draws the tray icon image. |

The script does not call an external API; it builds a Teams URL and asks Windows to open it.

---

## Set Up Class Codes

### Find Your Meeting Details

For every class, collect:

1. Its meeting ID, normally a 10-15 digit number.
2. Its passcode, normally a short alphanumeric value.

You can find these in a lecturer's email or Moodle post, the Teams calendar event, or the channel description.

### Create `teams_codes.txt`

Create `teams_codes.txt` next to `class_links.py`. Each non-comment line has this format:

```text
Class Name | Meeting ID | Passcode
```

Example using placeholder codes:

```text
# Morning classes
Data Structures | 123456789012 | ABC123
Database Systems | 987654321098 | XYZ789

# Afternoon classes
Operating Systems | 111222333444 | DEF456
Computer Networks | 555666777888 | GHI789
```

Rules:

- The pipe (`|`) separates the class name, meeting ID, and passcode.
- Spaces around pipes are optional.
- Meeting IDs may include spaces; the script removes them.
- Lines beginning with `#` are comments.
- A line with anything other than exactly three fields is skipped with a warning.

---

## Folder Layout

```text
Assignment Checker/
|-- class_links.py
|-- teams_codes.txt
`-- ClassLinks.md
```

Keep `teams_codes.txt` private. Meeting IDs and passcodes may allow someone to join your classes.

---

## Run the App

### From VS Code

Open a terminal in the project folder and run:

```powershell
python class_links.py
```

A tray icon appears. Left-click it to show the classes; right-click it and select **Quit** to stop the app.

### At Login with Task Scheduler

1. Open **Task Scheduler** and choose **Create Task**.
2. In **General**, name it `Class Links` and select **Run only when user is logged on**.
3. In **Triggers**, create an **At log on** trigger.
4. In **Actions**, add a **Start a program** action.
5. Set **Program/script** to the full path of `python.exe`. Use `where.exe python` in PowerShell to find it.
6. Set **Add arguments** to `class_links.py`.
7. Set **Start in** to the full path of the `Assignment Checker` folder.
8. In **Conditions**, clear **Start the task only if the computer is on AC power**.

You do not need Task Scheduler to use Class Links. Run `python class_links.py` from the project folder whenever you need it; a small purple circle appears in the system tray near the clock.

### Without a Console Window

Create `launch_classlinks.vbs` in the project folder and adjust the paths if required:

```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\Users\glori\AppData\Local\Programs\Python\Python313\pythonw.exe"" ""C:\Users\glori\OneDrive\Documents\GitHub\Assignment Checker\class_links.py""", 0, False
```

Configure Task Scheduler to run `wscript.exe`, with the full VBS path as its argument. `pythonw.exe` runs Python without a console window.

---

## Using Class Links

### Tray Icon

- Left-click: show or hide the window.
- Right-click: show/hide, reload codes, and quit actions.

### Window Controls

- Click a class: open its Teams meeting. The window hides shortly afterward.
- Refresh button: re-read `teams_codes.txt`.
- Close button: hide the window without quitting.
- Drag the window: reposition it.

Class buttons highlight on hover to indicate they are clickable.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Missing `teams_codes.txt` | Create it next to `class_links.py`. |
| No classes loaded | Ensure each class uses exactly three `|`-separated fields. |
| Some classes are missing | Check the terminal warning for the skipped line number and correct its format. |
| Click does nothing | Reinstall Teams or configure Windows to use Teams for the `msteams` protocol. |
| A meeting opens in the browser | Check **Settings > Apps > Default apps > Choose defaults by protocol** for `msteams`. |
| The wrong meeting opens | Check that the meeting ID and passcode are not swapped or outdated. |
| Tray icon disappears | Check the terminal for an application error. |
| Two tray icons appear | Quit both instances, then run the program once. |

### Force Browser Mode

If the Teams protocol is not registered, replace `join_class` in `class_links.py` with:

```python
def join_class(meeting_id, passcode):
	webbrowser.open(f"https://teams.microsoft.com/meet/{meeting_id}?p={passcode}")
```

---

## Updating Codes

When your classes change, edit `teams_codes.txt`, save it, and select the refresh button in the Class Links window. No restart is needed.

---

## Configuration

The main setting near the top of `class_links.py` is:

```python
HIDE_AFTER_JOIN = True
```

Set it to `False` to keep the window open after selecting a class.

---

## Privacy and Security

`teams_codes.txt` contains meeting credentials. Do not commit it to GitHub, share it in chat, or email it. If it is exposed, ask the lecturer to replace the passcode or meeting link.

The script makes no network requests itself. It only constructs a URL for Windows to open.

---

## Credits

- [pystray](https://github.com/moses-palmer/pystray)
- Microsoft Teams `msteams://` URL protocol

## License

Personal use. Modify freely.
