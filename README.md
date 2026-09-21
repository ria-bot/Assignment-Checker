# 🎓 Strathmore Assignment Hub

A cross-platform desktop utility built for Strathmore University students. It automatically aggregates upcoming assignments from **Google Classroom** and **Strathmore eLearning (Moodle)** into clean, interactive desktop sticky notes.

---

## ✨ Features

- **Domain-Enforced Google Sign-In**: Integrated OAuth 2.0 PKCE flow restricted to `@strathmore.edu` email accounts.
- **Automated eLearning Authentication**: Generates Moodle Web Service tokens on demand without requiring students to manually extract API keys.
- **AES-256 Local Encryption**: Safely encrypts refresh tokens and session credentials locally using `cryptography.fernet` and system keyrings (KWallet, GNOME Keyring, Windows Credential Manager).
- **Desktop Sticky Notes**: Movable, frameless, stay-on-top desktop widgets built with Tkinter.
- **Cross-Platform Compatibility**: Native standalone binary support for Linux and Windows.

---

## 🐧 Quick Start for Linux Users (Installing the Executable)

Non-technical users on Linux, including Ubuntu, Debian, Arch Linux, and Fedora, do **not** need Python, `pip`, or any dependencies installed.

### Step 1: Download or Locate the Executable

Navigate to the directory containing the compiled binary, such as `dist/StrathmoreAssignmentHub`, or the directory containing the downloaded release.

### Step 2: Grant Executable Permissions

Open a terminal in that folder and run:

```bash
chmod +x StrathmoreAssignmentHub
```

Alternatively, right-click the file in your file manager, open **Properties**, select **Permissions**, and check **Allow executing file as program**.

### Step 3: Launch the Application

Launch the application directly from the terminal:

```bash
./StrathmoreAssignmentHub
```

---

## 🛠️ Developer Setup & Building

### 1. Development Prerequisites (Linux)

Install standard C audio and system notification libraries:

```bash
# Arch Linux
sudo pacman -S python-pip portaudio ffmpeg libnotify

# Ubuntu / Debian
sudo apt install python3-pip python3-venv portaudio19-dev ffmpeg libnotify-bin
```

### 2. Environment Setup

```bash
### Clone the repository and navigate inside

cd Assignment-Checker

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Build the Standalone Executable

The repository includes a PyInstaller specification file:

```bash
pip install pyinstaller
pyinstaller StrathmoreAssignmentHub.spec
```

The resulting executable is placed in the `dist/` directory.

---

## 🔒 Security & Privacy Notice

- **No Plaintext Passwords Stored**: eLearning passwords are used only during initial login to request an API token, then discarded immediately from memory.
- **Local Storage Only**: Tokens are stored encrypted on disk in `user_data.enc` and protected using your system's native secret manager.
