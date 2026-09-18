# 📌 Home Checker

A desktop widget that watches your **Google Classroom** and **Strathmore eLearning (Moodle)** accounts and shows you what's due — today, this week, this month, and anything with no due date at all.

It lives quietly in your system tray and only pops up when you need it.

---

## What It Does

- **Pulls assignments from two places at once:**
  - Google Classroom (via the official API)
  - Moodle / Strathmore eLearning (via the Moodle Web Services API)
- **Groups them by urgency:**
  - 🎓 Google Classroom — due today
  - 📚 Strathmore eLearning — due today
  - 📅 This Week — anything due in the next 7 days
  - 📆 This Month — anything due in the next 30 days
  - 📋 No Due Date — anything unsubmitted with no deadline
- **Countdown chips** — each upcoming item shows "2 days", "5 days", etc.
- **Mark as done manually** — click any item to mark it done with a reason (group work, offline submission, partial, other) and an optional note.
- **Auto-tracking** — anything you actually submit in Classroom or Moodle is detected and logged to history automatically.
- **History log** — every mark-done event is saved to `history.json` with a reason and date.
- **Toast notifications** — a Windows notification fires when a new assignment appears.
- **Tray icon color** — 🟡 yellow when all clear, 🔴 red when something's unsubmitted and due today.
- **Auto-refresh** every 15 minutes.
- **Daily reset** of the "marked done" list, so nothing hides permanently.

---

## What You Need Before Starting

### Software
- **Windows 10 or 11**
- **Python 3.10 or newer** — [download here](https://www.python.org/downloads/)
  - ⚠️ During installation, tick **"Add Python to PATH"**
- **Visual Studio Code** (optional, but recommended) — [download here](https://code.visualstudio.com/)

### Accounts
- A **Google account** with access to Google Classroom
- A **Strathmore eLearning account** (or any Moodle site — the URL is configurable)

---

## Step 1: Install the Python Libraries

Open PowerShell (press `Win`, type `powershell`, hit Enter) and run:

```powershell
python -m pip install 
google-api-python-client 
google-auth-httplib2 
google-auth-oauthlib pystray pillow 
winotify
```


This installs:

| Library | What it does |
|---|---|
| `google-api-python-client` | Talks to Google Classroom |
| `google-auth-*` | Handles Google login |
| `pystray` | Creates the system tray icon |
| `pillow` | Draws the tray icon image |
| `winotify` | Sends Windows toast notifications |

Moodle uses only Python's standard library, so nothing extra needed for that side.

---

## Step 2: Set Up Google Classroom Access

The script needs a `credentials.json` file from Google Cloud Console so it can talk to your Classroom account.

1. Go to [console.cloud.google.com](https://console.cloud.google.com/) and sign in with your school Google account.
2. Create a new project — name it something like `home-checker`.
3. Go to **APIs & Services → Library**, search for **"Google Classroom API"**, and click **Enable**.
4. Go to **APIs & Services → OAuth consent screen**:
   - User type: **External**
   - App name: anything
   - Support/developer email: your email
   - Save and continue
   - Under **Test users**, add your own Google email
5. Go to **APIs & Services → Credentials**:
   - Click **Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Name: anything
   - Click **Create**, then **Download JSON**
6. **Rename the downloaded file to `credentials.json`** and move it into the same folder as `homechecker.py`.

The first time you run the script, a browser window will open asking you to authorize. Click **Allow**. A `token.json` file will be created automatically so you won't be asked again.

---

## Step 3: Set Up Moodle Access

You need a Moodle API token so the script can read your assignments.

### Get Your Token

Open PowerShell and paste this (replace with your own credentials, like the username, you use your student number and the password you use your password that you set on the ams):

```powershell
$body = @{
  username = "YOUR_MOODLE_USERNAME"
  password = "YOUR_MOODLE_PASSWORD"
  service = "moodle_mobile_app"
}

Invoke-RestMethod -Uri "https://elearning.strathmore.edu/login/token.php" -Method Post -Body $body
```

If successful, the response contains a long `token` value. Create `moodle_token.txt` in the same folder as `homechecker.py`, then paste only that token into the file. Do not add quotes or spaces.

### If That URL Is Not Yours

For another Moodle site, change the URL to, you should see the website with your name and profile there:

```text
https://YOUR-MOODLE-SITE/login/token.php
```

### Get Your Moodle User ID

Run this in PowerShell, replacing the token with yours, the token you got from the powershell:

```powershell
$token = "PASTE_YOUR_TOKEN_HERE"
$url = "https://elearning.strathmore.edu/webservice/rest/server.php?wstoken=$token&wsfunction=core_webservice_get_site_info&moodlewsrestformat=json"
$response = Invoke-RestMethod -Uri $url
Write-Host "Your userid is: $($response.userid)"
```

Replace the value in this `homechecker.py` setting with that number:

```python
MOODLE_USERID = 57548
```

---

## Step 4: Folder Layout

```text
Assignment Checker/
|-- homechecker.py
|-- credentials.json
|-- token.json
|-- moodle_token.txt
|-- done.json
|-- history.json
`-- HomeChecker.md
```

Never share or upload `credentials.json`, `token.json`, or `moodle_token.txt`. They provide access to your accounts. These are very sensitive documents, if you have shared, pray you wont be hacked or just refresh the whole process

---

## Step 5: Choose How to Run It

### Option A: Run Inside VS Code

Open a terminal in the project folder and run:

```powershell
python homechecker.py
```

A tray icon appears, go to your taskbar and press the ^, you should see a yellow circle there called homechecker. Right-click it and select **Quit** to stop the app, pressing the X just hides it.

### Option B: Run at Login with Task Scheduler

1. Open **Task Scheduler** and select **Create Task**.
2. On **General**, name it `Home Checker` and select **Run only when user is logged on**.
3. On **Triggers**, create an **At log on** trigger.
4. On **Actions**, create a **Start a program** action.
5. Set **Program/script** to your full `python.exe` path, or any python app you have in your pc, but highly recommend you use this one. Find it with `where.exe python`.
6. Set **Add arguments** to `homechecker.py` and **Start in** to the full project-folder path.
7. On **Conditions**, clear **Start the task only if the computer is on AC power**.

### Option C: Run Without a Console Window

Create `launch_homechecker.vbs` in the project folder, adjusting paths as needed:

```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\Users\glori\AppData\Local\Programs\Python\Python313\pythonw.exe"" ""C:\Users\glori\OneDrive\Documents\GitHub\Assignment Checker\homechecker.py""", 0, False
```

In Task Scheduler, run `wscript.exe` with the VBS file path as its argument.

---

## How to Use It

### Tray Icon

- Left-click: show or hide the window.
- Right-click: show/hide, refresh, history, and quit actions.

### Inside the Window

- Use the refresh button to fetch assignments immediately.
- Use the history button to open the history panel.
- Click an item to mark it done with a reason and optional note.
- Scroll with the mouse wheel or scrollbar.

### Marking Items as Done

Choose **Group work**, **Offline submission**, **Partial**, or **Other**, then optionally add a note. The item is hidden for the day and the action is recorded in `history.json`.

### History Panel

The panel shows the total logged assignments, a breakdown by reason, and the latest 50 entries.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` on startup | Re-run the Step 1 install command. |
| `FileNotFoundError: credentials.json` | Download the Google credentials file and put it in the project folder. |
| Browser does not open at first run | Add your account as a Google OAuth test user. |
| `invalid_grant` | Delete `token.json`, then run the app to authorize again. |
| Moodle reports an invalid token | Regenerate it at `https://elearning.strathmore.edu/user/managetoken.php` and update `moodle_token.txt`. |
| Moodle has no assignments | Confirm `MOODLE_USERID` is your Moodle user ID. |
| Toasts do not appear | Turn off Windows Focus Assist. |
| Tray icon disappears | Check the terminal for a crash or duplicate Task Scheduler entry. |
| Two tray icons appear | Quit both, then launch the app once. |

---

## Configuration

All settings are at the top of `homechecker.py`:

```python
MOODLE_URL = "https://elearning.strathmore.edu/webservice/rest/server.php"
MOODLE_USERID = 57548
LOCAL_TZ_OFFSET = datetime.timedelta(hours=3)
REFRESH_MINUTES = 15
UNDATED_LIMIT = 5
WEEK_LIMIT = 6
MONTH_LIMIT = 12
```

Restart the app after changing a setting.

---

## Privacy and Security

The application uses Google OAuth to read coursework and a personal Moodle token to read courses and assignments. It sends data only to the Google and Moodle APIs.

Keep `credentials.json`, `token.json`, and `moodle_token.txt` private. Do not commit them to GitHub or share them in messages or email.

---

## Credits

- [Google Classroom API](https://developers.google.com/classroom)
- [Moodle Web Services](https://docs.moodle.org/dev/Web_services)
- [pystray](https://github.com/moses-palmer/pystray)
- [winotify](https://github.com/versa-syahptr/winotify)

## License

Personal use. Modify freely.
