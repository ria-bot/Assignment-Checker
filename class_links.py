import os
import webbrowser
import threading
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageDraw
import pystray

BASE_DIR = r"/home/topsy/Documents/Assignment-Checker"
CODES_FILE = os.path.join(BASE_DIR, "teams_codes.txt")

HIDE_AFTER_JOIN = True  # set False if you want the window to stay open after clicking


def load_classes():
    """Returns list of (name, id, passcode) from teams_codes.txt."""
    if not os.path.exists(CODES_FILE):
        messagebox.showerror(
            "Missing file",
            f"Could not find:\n{CODES_FILE}\n\nCreate it with lines like:\n"
            f"Class Name | 123456789012 | ABC123"
        )
        return []

    classes = []
    with open(CODES_FILE, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3:
                print(f"Skipping line {lineno} (need 3 fields): {line}")
                continue
            name, mid, pwd = parts
            mid = mid.replace(" ", "").replace("-", "")
            classes.append((name, mid, pwd))
    return classes


def build_url(meeting_id, passcode):
    return f"msteams://teams.microsoft.com/meet/{meeting_id}?p={passcode}"


def open_url(url):
    """Try the msteams:// protocol, fall back to https:// in browser."""
    try:
        os.startfile(url)
        return True
    except Exception:
        return False


def join_class(meeting_id, passcode):
    msteams_url = build_url(meeting_id, passcode)
    https_url = f"https://teams.microsoft.com/meet/{meeting_id}?p={passcode}"
    if not open_url(msteams_url):
        webbrowser.open(https_url)


class ClassNote:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Class Links")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#E8D5F0")
        self.root.withdraw()  # start hidden

        width, height = 320, 420
        screen_w = self.root.winfo_screenwidth()
        x = screen_w - width - 30
        y = 60
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # Header
        header = tk.Frame(self.root, bg="#5B2D7A", height=36)
        header.pack(fill="x")
        tk.Label(
            header, text="🎓  Class Links", bg="#5B2D7A", fg="white",
            font=("Segoe UI", 11, "bold"), padx=10
        ).pack(side="left", pady=6)

        close_btn = tk.Label(
            header, text="✕", bg="#5B2D7A", fg="white",
            font=("Segoe UI", 12, "bold"), cursor="hand2", padx=12
        )
        close_btn.pack(side="right", pady=4)
        close_btn.bind("<Button-1>", lambda e: self.hide())

        reload_btn = tk.Label(
            header, text="⟳", bg="#5B2D7A", fg="white",
            font=("Segoe UI", 13, "bold"), cursor="hand2", padx=10
        )
        reload_btn.pack(side="right", pady=4)
        reload_btn.bind("<Button-1>", lambda e: self.reload())

        # Body
        self.body = tk.Frame(self.root, bg="#E8D5F0")
        self.body.pack(fill="both", expand=True, padx=12, pady=10)

        # Drag
        def start_move(e):
            self.root.x = e.x
            self.root.y = e.y

        def do_move(e):
            x = e.x_root - self.root.x
            y = e.y_root - self.root.y
            self.root.geometry(f"+{x}+{y}")

        for w in (self.root, header):
            w.bind("<Button-1>", start_move)
            w.bind("<B1-Motion>", do_move)

        self.reload()

    def reload(self):
        for w in self.body.winfo_children():
            w.destroy()

        classes = load_classes()
        if not classes:
            tk.Label(
                self.body, text="No classes loaded.\nCheck teams_codes.txt",
                bg="#E8D5F0", fg="#900",
                font=("Segoe UI", 10), justify="left"
            ).pack(anchor="w")
            return

        for name, mid, pwd in classes:
            self._add_button(name, mid, pwd)

    def _add_button(self, name, mid, pwd):
        btn = tk.Label(
            self.body,
            text=f"▶  {name}",
            bg="#F8F0FC", fg="#2A1A3A",
            font=("Segoe UI", 10, "bold"),
            anchor="w", padx=10, pady=8,
            cursor="hand2", bd=0
        )
        btn.pack(fill="x", pady=3)

        def on_enter(e):
            btn.configure(bg="#D5A6E8")

        def on_leave(e):
            btn.configure(bg="#F8F0FC")

        def on_click(e):
            join_class(mid, pwd)
            if HIDE_AFTER_JOIN:
                self.root.after(400, self.hide)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.bind("<Button-1>", on_click)

    def show(self):
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self.root.withdraw()

    def toggle(self):
        if self.root.state() == "withdrawn":
            self.show()
        else:
            self.hide()

    def run(self):
        self.root.mainloop()


def make_icon_image():
    img = Image.new("RGB", (64, 64), "#333333")
    d = ImageDraw.Draw(img)
    d.ellipse((10, 10, 54, 54), fill="#B070E0")  # purple
    return img


def main():
    win = ClassNote()

    def on_toggle(icon, item):
        win.root.after(0, win.toggle)

    def on_reload(icon, item):
        win.root.after(0, win.reload)
        if win.root.state() == "withdrawn":
            win.root.after(0, win.show)

    def on_quit(icon, item):
        icon.stop()
        win.root.after(0, win.root.quit)

    menu = pystray.Menu(
        pystray.MenuItem("Show / Hide", on_toggle, default=True),
        pystray.MenuItem("Reload codes", on_reload),
        pystray.MenuItem("Quit", on_quit),
    )
    icon = pystray.Icon("classlinks", make_icon_image(), "Class Links", menu)

    threading.Thread(target=icon.run, daemon=True).start()
    win.run()


if __name__ == "__main__":
    main()