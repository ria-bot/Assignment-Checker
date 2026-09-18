import os
import json
import datetime
import threading
import tkinter as tk
import urllib.parse
import urllib.request

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from PIL import Image, ImageDraw
import pystray
from winotify import Notification, audio

# ---------- Config ----------
BASE_DIR = r"C:\Users\glori\OneDrive\Documents\GitHub\Assignment Checker"
CREDS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
MOODLE_TOKEN_FILE = os.path.join(BASE_DIR, "moodle_token.txt")
DONE_FILE = os.path.join(BASE_DIR, "done.json")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

MOODLE_URL = "https://elearning.strathmore.edu/webservice/rest/server.php"
MOODLE_USERID = 57548
LOCAL_TZ_OFFSET = datetime.timedelta(hours=3)  # Kenya

REFRESH_MINUTES = 15
UNDATED_LIMIT = 5
WEEK_LIMIT = 6
MONTH_LIMIT = 12

REASONS = [
    ("group",   "Group work — someone else submitted"),
    ("offline", "Offline submission (paper, in-class)"),
    ("partial", "Partial — my part is done"),
    ("other",   "Other (add a note)"),
]

CLASSROOM_SCOPES = [
    'https://www.googleapis.com/auth/classroom.student-submissions.me.readonly',
    'https://www.googleapis.com/auth/classroom.courses.readonly',
]


# ---------- Small JSON helpers ----------
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"(save_json failed: {e})")


def today_str():
    return (datetime.datetime.now(datetime.timezone.utc) + LOCAL_TZ_OFFSET).strftime("%Y-%m-%d")


# ---------- Google Classroom ----------
def get_classroom_creds():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, CLASSROOM_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, CLASSROOM_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


def fetch_classroom_assignments():
    creds = get_classroom_creds()
    service = build("classroom", "v1", credentials=creds)
    courses = service.courses().list(courseStates="ACTIVE").execute().get("courses", [])

    local_now = datetime.datetime.now(datetime.timezone.utc) + LOCAL_TZ_OFFSET
    today_local = local_now.date()
    week_end = today_local + datetime.timedelta(days=7)
    month_end = today_local + datetime.timedelta(days=30)

    due_today, this_week, this_month, undated = [], [], [], []

    for course in courses:
        course_id = course["id"]
        course_name = course["name"]
        works = service.courses().courseWork().list(
            courseId=course_id, courseWorkStates="PUBLISHED"
        ).execute().get("courseWork", [])

        for work in works:
            subs = service.courses().courseWork().studentSubmissions().list(
                courseId=course_id, courseWorkId=work["id"], userId="me"
            ).execute().get("studentSubmissions", [])
            state = subs[0].get("state") if subs else "NEW"
            submitted = state in ("TURNED_IN", "RETURNED")

            entry = {
                "source": "classroom",
                "course": course_name,
                "title": work["title"],
                "submitted": submitted,
                "key": f"classroom::{course_id}::{work['id']}",
            }

            if "dueDate" not in work:
                if not submitted:
                    entry["due_str"] = "no due date"
                    entry["days_left"] = None
                    undated.append(entry)
                continue

            dd = work["dueDate"]
            dt = work.get("dueTime", {"hours": 23, "minutes": 59})
            due_utc = datetime.datetime(
                dd["year"], dd["month"], dd["day"],
                dt.get("hours", 23), dt.get("minutes", 59),
                tzinfo=datetime.timezone.utc,
            )
            due_local = due_utc + LOCAL_TZ_OFFSET
            days_left = (due_local.date() - today_local).days
            entry["days_left"] = days_left

            if due_local.date() == today_local:
                entry["due_str"] = due_local.strftime("%I:%M %p").lstrip("0")
                due_today.append(entry)
            elif today_local < due_local.date() <= week_end:
                entry["due_str"] = due_local.strftime("%a %I:%M %p").lstrip("0")
                this_week.append(entry)
            elif week_end < due_local.date() <= month_end:
                entry["due_str"] = due_local.strftime("%a %d %b")
                this_month.append(entry)

    return due_today, this_week, this_month, undated


# ---------- Moodle ----------
def load_moodle_token():
    with open(MOODLE_TOKEN_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def call_moodle(token, function, **params):
    query = {
        "wstoken": token,
        "wsfunction": function,
        "moodlewsrestformat": "json",
    }
    query.update(params)
    url = MOODLE_URL + "?" + urllib.parse.urlencode(query)
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_moodle_assignments():
    token = load_moodle_token()
    local_now = datetime.datetime.now(datetime.timezone.utc) + LOCAL_TZ_OFFSET
    today_local = local_now.date()
    today_start = datetime.datetime.combine(today_local, datetime.time.min)
    today_end = today_start + datetime.timedelta(days=1)

    start_ts = int((today_start - LOCAL_TZ_OFFSET).timestamp())
    end_ts = int((today_end - LOCAL_TZ_OFFSET).timestamp())
    week_end_ts = int((today_start + datetime.timedelta(days=7) - LOCAL_TZ_OFFSET).timestamp())
    month_end_ts = int((today_start + datetime.timedelta(days=30) - LOCAL_TZ_OFFSET).timestamp())

    courses = call_moodle(token, "core_enrol_get_users_courses", userid=MOODLE_USERID)
    if isinstance(courses, dict) and courses.get("exception"):
        raise RuntimeError(courses.get("message", "Moodle error"))

    due_today, this_week, this_month, undated = [], [], [], []

    for course in courses:
        course_id = course["id"]
        course_name = course["fullname"]
        data = call_moodle(
            token, "mod_assign_get_assignments",
            **{"courseids[0]": course_id},
        )
        if not isinstance(data, dict) or "courses" not in data:
            continue

        for c in data["courses"]:
            for a in c.get("assignments", []):
                sub = call_moodle(
                    token, "mod_assign_get_submissions",
                    **{"assignmentids[0]": a["id"]},
                )
                submitted = False
                try:
                    for s_course in sub.get("assignments", []):
                        for s in s_course.get("submissions", []):
                            if s.get("userid") == MOODLE_USERID and s.get("status") == "submitted":
                                submitted = True
                except Exception:
                    pass

                due = a.get("duedate", 0)
                entry = {
                    "source": "moodle",
                    "course": course_name,
                    "title": a["name"],
                    "submitted": submitted,
                    "key": f"moodle::{a['id']}",
                }

                if not due:
                    if not submitted:
                        entry["due_str"] = "no due date"
                        entry["days_left"] = None
                        undated.append(entry)
                    continue

                due_local = datetime.datetime.fromtimestamp(
                    due, tz=datetime.timezone.utc
                ) + LOCAL_TZ_OFFSET
                days_left = (due_local.date() - today_local).days
                entry["days_left"] = days_left

                if start_ts <= due < end_ts:
                    entry["due_str"] = due_local.strftime("%I:%M %p").lstrip("0")
                    due_today.append(entry)
                elif end_ts <= due < week_end_ts:
                    entry["due_str"] = due_local.strftime("%a %I:%M %p").lstrip("0")
                    this_week.append(entry)
                elif week_end_ts <= due < month_end_ts:
                    entry["due_str"] = due_local.strftime("%a %d %b")
                    this_month.append(entry)

    return due_today, this_week, this_month, undated


# ---------- Notification ----------
def send_toast(title, message):
    try:
        t = Notification(
            app_id="Windows PowerShell",
            title=title, msg=message, duration="long",
        )
        t.set_audio(audio.Default, loop=False)
        t.show()
    except Exception as e:
        print(f"(Toast failed: {e})")


# ---------- History ----------
def append_history(entry):
    hist = load_json(HISTORY_FILE, [])
    hist.append(entry)
    save_json(HISTORY_FILE, hist)


def log_api_submissions(items):
    hist = load_json(HISTORY_FILE, [])
    known = {(h.get("key"), h.get("reason")) for h in hist}
    for it in items:
        if it.get("submitted") and (it["key"], "api") not in known:
            hist.append({
                "key": it["key"],
                "title": it["title"],
                "course": it["course"],
                "source": it["source"],
                "reason": "api",
                "note": "",
                "date": today_str(),
            })
    save_json(HISTORY_FILE, hist)


# ---------- Dialogs ----------
def ask_reason_and_note(parent, title):
    dlg = tk.Toplevel(parent)
    dlg.title("Mark as done")
    dlg.configure(bg="#F0F0F0")
    dlg.geometry("380x320")
    dlg.attributes("-topmost", True)
    dlg.grab_set()

    tk.Label(
        dlg, text=title, bg="#F0F0F0", fg="#123",
        font=("Segoe UI", 10, "bold"),
        wraplength=340, justify="left",
    ).pack(anchor="w", padx=14, pady=(14, 6))

    tk.Label(
        dlg, text="Why are you marking this done?",
        bg="#F0F0F0", fg="#456", font=("Segoe UI", 9),
    ).pack(anchor="w", padx=14)

    choice = tk.StringVar(value=REASONS[0][0])
    for val, label in REASONS:
        tk.Radiobutton(
            dlg, text=label, variable=choice, value=val,
            bg="#F0F0F0", anchor="w", font=("Segoe UI", 9),
        ).pack(fill="x", padx=20, pady=1)

    tk.Label(
        dlg, text="Notes (optional):",
        bg="#F0F0F0", fg="#456", font=("Segoe UI", 9),
    ).pack(anchor="w", padx=14, pady=(8, 2))

    note_box = tk.Text(dlg, height=3, width=44, font=("Segoe UI", 9))
    note_box.pack(padx=14)

    result = {"reason": None, "note": None}

    def on_ok():
        result["reason"] = choice.get()
        result["note"] = note_box.get("1.0", "end").strip()
        dlg.destroy()

    def on_cancel():
        dlg.destroy()

    btn_frame = tk.Frame(dlg, bg="#F0F0F0")
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side="left", padx=6)
    tk.Button(btn_frame, text="Mark Done", command=on_ok, width=12).pack(side="left", padx=6)

    parent.wait_window(dlg)
    return result["reason"], result["note"]


def show_history_popup(parent):
    hist = load_json(HISTORY_FILE, [])
    dlg = tk.Toplevel(parent)
    dlg.title("History")
    dlg.configure(bg="#F0F0F0")
    dlg.geometry("480x520")
    dlg.attributes("-topmost", True)

    tk.Label(
        dlg, text="📊 Assignment History", bg="#F0F0F0", fg="#123",
        font=("Segoe UI", 13, "bold"),
    ).pack(anchor="w", padx=14, pady=(14, 4))

    total = len(hist)
    api = sum(1 for h in hist if h.get("reason") == "api")
    manual = total - api
    group = sum(1 for h in hist if h.get("reason") == "group")
    offline = sum(1 for h in hist if h.get("reason") == "offline")
    partial = sum(1 for h in hist if h.get("reason") == "partial")
    other = sum(1 for h in hist if h.get("reason") == "other")

    summary = (
        f"Total logged: {total}\n"
        f"  ✅ Via API:     {api}\n"
        f"  ✋ Manual:      {manual}\n"
        f"     ├ Group:    {group}\n"
        f"     ├ Offline:  {offline}\n"
        f"     ├ Partial:  {partial}\n"
        f"     └ Other:    {other}"
    )
    tk.Label(
        dlg, text=summary, bg="#F0F0F0", fg="#234",
        font=("Consolas", 9), justify="left",
    ).pack(anchor="w", padx=14, pady=(0, 10))

    tk.Label(
        dlg, text="Recent (last 50):", bg="#F0F0F0", fg="#456",
        font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w", padx=14)

    frame = tk.Frame(dlg, bg="#F0F0F0")
    frame.pack(fill="both", expand=True, padx=14, pady=(4, 14))

    scroll = tk.Scrollbar(frame)
    scroll.pack(side="right", fill="y")
    txt = tk.Text(
        frame, wrap="word", yscrollcommand=scroll.set,
        font=("Consolas", 9), bg="white",
    )
    txt.pack(side="left", fill="both", expand=True)
    scroll.config(command=txt.yview)

    for h in reversed(hist[-50:]):
        mark = "✅" if h.get("reason") == "api" else "✋"
        note = f"  — {h['note']}" if h.get("note") else ""
        line = (
            f"{h.get('date', '?')}  {mark}  {h.get('title', '?')}\n"
            f"           {h.get('course', '?')}  [{h.get('reason', '?')}]{note}\n\n"
        )
        txt.insert("end", line)
    txt.config(state="disabled")

    tk.Button(dlg, text="Close", command=dlg.destroy, width=10).pack(pady=(0, 12))


# ---------- Main window ----------
class CheckerWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Home Checker")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#F0F0F0")
        self.root.withdraw()

        width, height = 420, 720
        screen_w = self.root.winfo_screenwidth()
        x = screen_w - width - 30
        y = 60
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # --- Header ---
        header = tk.Frame(self.root, bg="#333", height=36)
        header.pack(fill="x")
        tk.Label(
            header, text="📌  Home Checker", bg="#333", fg="white",
            font=("Segoe UI", 11, "bold"), padx=10,
        ).pack(side="left", pady=6)

        close_btn = tk.Label(
            header, text="✕", bg="#333", fg="white",
            font=("Segoe UI", 12, "bold"), cursor="hand2", padx=12,
        )
        close_btn.pack(side="right", pady=4)
        close_btn.bind("<Button-1>", lambda e: self.hide())

        refresh_btn = tk.Label(
            header, text="⟳", bg="#333", fg="white",
            font=("Segoe UI", 13, "bold"), cursor="hand2", padx=10,
        )
        refresh_btn.pack(side="right", pady=4)
        refresh_btn.bind("<Button-1>", lambda e: self.refresh(manual=True))

        history_btn = tk.Label(
            header, text="📊", bg="#333", fg="white",
            font=("Segoe UI", 12, "bold"), cursor="hand2", padx=10,
        )
        history_btn.pack(side="right", pady=4)
        history_btn.bind("<Button-1>", lambda e: show_history_popup(self.root))

        # --- Scrollable body ---
        body_outer = tk.Frame(self.root, bg="#F0F0F0")
        body_outer.pack(fill="both", expand=True)

        self.body_canvas = tk.Canvas(
            body_outer, bg="#F0F0F0", highlightthickness=0,
        )
        self.body_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(
            body_outer, orient="vertical", command=self.body_canvas.yview,
        )
        scrollbar.pack(side="right", fill="y")
        self.body_canvas.configure(yscrollcommand=scrollbar.set)

        self.body = tk.Frame(self.body_canvas, bg="#F0F0F0")
        self.body_window = self.body_canvas.create_window(
            (0, 0), window=self.body, anchor="nw",
        )

        def _on_body_configure(event):
            self.body_canvas.configure(scrollregion=self.body_canvas.bbox("all"))
            self.body_canvas.itemconfig(
                self.body_window, width=self.body_canvas.winfo_width()
            )

        self.body.bind("<Configure>", _on_body_configure)
        self.body_canvas.bind(
            "<Configure>",
            lambda e: self.body_canvas.itemconfig(self.body_window, width=e.width),
        )

        def _on_mousewheel(event):
            self.body_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(_):
            self.body_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(_):
            self.body_canvas.unbind_all("<MouseWheel>")

        self.root.bind("<Enter>", _bind_wheel)
        self.root.bind("<Leave>", _unbind_wheel)

        # --- State ---
        self.seen_keys = set()
        self.first_run_done = False
        self.done = load_json(DONE_FILE, {})

        # --- Window drag ---
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

        self.refresh(manual=False)

    def is_done(self, key):
        return key in self.done

    def mark_done(self, item):
        reason, note = ask_reason_and_note(self.root, item["title"])
        if not reason:
            return

        self.done[item["key"]] = {"date": today_str()}
        save_json(DONE_FILE, self.done)

        append_history({
            "key": item["key"],
            "title": item["title"],
            "course": item["course"],
            "source": item["source"],
            "reason": reason,
            "note": note,
            "date": today_str(),
        })

        send_toast("✅ Marked done", f"{item['title']} — {reason}")
        self.refresh(manual=True)

    def clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    def add_section(self, title, color, items, error=None, cap=None):
        frame = tk.Frame(self.body, bg=color)
        frame.pack(fill="x", padx=12, pady=(0, 10))

        tk.Label(
            frame, text=title, bg=color, fg="#123",
            font=("Segoe UI", 11, "bold"), anchor="w", padx=10, pady=6,
        ).pack(fill="x")

        inner = tk.Frame(frame, bg=color)
        inner.pack(fill="x", padx=10, pady=(0, 8))

        if error:
            tk.Label(
                inner, text=f"Error: {error}", bg=color, fg="#900",
                font=("Segoe UI", 9), wraplength=360, justify="left", anchor="w",
            ).pack(anchor="w")
        elif not items:
            tk.Label(
                inner, text="Nothing here ✓", bg=color, fg="#456",
                font=("Segoe UI", 10), anchor="w",
            ).pack(anchor="w")
        else:
            shown = items[:cap] if cap else items
            for it in shown:
                self._add_item_row(inner, color, it)
            if cap and len(items) > cap:
                tk.Label(
                    inner, text=f"+{len(items) - cap} more",
                    bg=color, fg="#567",
                    font=("Segoe UI", 8, "italic"), anchor="w",
                ).pack(anchor="w", pady=(4, 0))

    def _add_item_row(self, parent, color, it):
        row = tk.Frame(parent, bg=color, cursor="hand2")
        row.pack(fill="x", pady=(3, 0))

        mark = "✅" if it["submitted"] else "⬜"
        cb = tk.Label(
            row, text=mark, bg=color, fg="#123",
            font=("Segoe UI", 12, "bold"), cursor="hand2",
        )
        cb.pack(side="left", padx=(0, 6))

        # Countdown chip
        days_left = it.get("days_left")
        if days_left is not None and days_left > 0:
            chip_text = "1 day" if days_left == 1 else f"{days_left} days"
            chip_color = "#FFB347" if days_left <= 3 else "#A0C0A0"
            chip = tk.Label(
                row, text=chip_text, bg=chip_color, fg="#222",
                font=("Segoe UI", 8, "bold"), padx=6, pady=2,
            )
            chip.pack(side="right", padx=(4, 0))

        text_frame = tk.Frame(row, bg=color)
        text_frame.pack(side="left", fill="x", expand=True)

        tk.Label(
            text_frame, text=it["title"], bg=color, fg="#123",
            font=("Segoe UI", 10, "bold"),
            wraplength=280, justify="left", anchor="w",
        ).pack(anchor="w")
        tk.Label(
            text_frame,
            text=f"{it['course']} · due {it['due_str']}",
            bg=color, fg="#678",
            font=("Segoe UI", 8), anchor="w",
        ).pack(anchor="w")

        def on_click(e):
            if not it["submitted"]:
                self.mark_done(it)

        for w in (row, cb, text_frame):
            w.bind("<Button-1>", on_click)
        for child in text_frame.winfo_children():
            child.bind("<Button-1>", on_click)

    def refresh(self, manual=False):
        self.clear_body()
        tk.Label(
            self.body, text="Loading assignments…",
            bg="#F0F0F0", fg="#555", font=("Segoe UI", 10),
        ).pack(anchor="w")

        results = {
            "classroom_due": None, "classroom_week": None,
            "classroom_month": None, "classroom_undated": None,
            "moodle_due": None, "moodle_week": None,
            "moodle_month": None, "moodle_undated": None,
            "classroom_err": None, "moodle_err": None,
        }

        def fetch_c():
            try:
                due, wk, mo, und = fetch_classroom_assignments()
                results["classroom_due"] = due
                results["classroom_week"] = wk
                results["classroom_month"] = mo
                results["classroom_undated"] = und
            except Exception as e:
                results["classroom_err"] = str(e)
            results["classroom_done"] = True

        def fetch_m():
            try:
                due, wk, mo, und = fetch_moodle_assignments()
                results["moodle_due"] = due
                results["moodle_week"] = wk
                results["moodle_month"] = mo
                results["moodle_undated"] = und
            except Exception as e:
                results["moodle_err"] = str(e)
            results["moodle_done"] = True

        threading.Thread(target=fetch_c, daemon=True).start()
        threading.Thread(target=fetch_m, daemon=True).start()

        def check_done():
            if results.get("classroom_done") and results.get("moodle_done"):
                c_due = results["classroom_due"] or []
                c_wk = results["classroom_week"] or []
                c_mo = results["classroom_month"] or []
                c_und = results["classroom_undated"] or []
                m_due = results["moodle_due"] or []
                m_wk = results["moodle_week"] or []
                m_mo = results["moodle_month"] or []
                m_und = results["moodle_undated"] or []

                log_api_submissions(
                    c_due + c_wk + c_mo + m_due + m_wk + m_mo + c_und + m_und
                )

                def keep(items):
                    return [x for x in items if not self.is_done(x["key"])]

                c_due, c_wk, c_mo, c_und = keep(c_due), keep(c_wk), keep(c_mo), keep(c_und)
                m_due, m_wk, m_mo, m_und = keep(m_due), keep(m_wk), keep(m_mo), keep(m_und)

                self.clear_body()

                self.add_section("🎓 Google Classroom", "#FFF8B0", c_due, results["classroom_err"])
                self.add_section("📚 Strathmore eLearning", "#D8ECFF", m_due, results["moodle_err"])

                week_items = c_wk + m_wk
                if week_items:
                    self.add_section("📅 This Week", "#FFE9C0", week_items, cap=WEEK_LIMIT)

                month_items = c_mo + m_mo
                if month_items:
                    self.add_section("📆 This Month", "#E0F0E0", month_items, cap=MONTH_LIMIT)

                if c_und or m_und:
                    self.add_section(
                        "📋 No Due Date (not submitted)",
                        "#E8E8E8",
                        c_und + m_und, cap=UNDATED_LIMIT,
                    )

                all_due = c_due + m_due
                current_keys = {it["key"] for it in all_due}

                if self.first_run_done:
                    new_items = [it for it in all_due if it["key"] not in self.seen_keys]
                    if new_items:
                        titles = ", ".join(it["title"] for it in new_items[:3])
                        if len(new_items) > 3:
                            titles += f", +{len(new_items) - 3} more"
                        send_toast(f"📌 {len(new_items)} new assignment(s)", titles)
                        self.root.after(0, self.show)

                self.seen_keys = current_keys
                self.first_run_done = True

                has_unsubmitted = any(not it["submitted"] for it in all_due)
                self.update_tray_color(has_unsubmitted)
            else:
                self.root.after(200, check_done)

        check_done()

    def update_tray_color(self, alert):
        if not hasattr(self, "tray_icon") or self.tray_icon is None:
            return
        try:
            self.tray_icon.icon = make_icon_image(alert)
        except Exception:
            pass

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

    def auto_refresh_loop(self):
        self.refresh(manual=False)
        self.root.after(REFRESH_MINUTES * 60 * 1000, self.auto_refresh_loop)

    def run(self):
        self.root.after(REFRESH_MINUTES * 60 * 1000, self.auto_refresh_loop)
        self.root.mainloop()


# ---------- Tray icon ----------
def make_icon_image(alert=False):
    color = "#E04040" if alert else "#FFD34D"
    img = Image.new("RGB", (64, 64), "#333333")
    d = ImageDraw.Draw(img)
    d.ellipse((10, 10, 54, 54), fill=color)
    return img


def main():
    win = CheckerWindow()

    def on_toggle(icon, item):
        win.root.after(0, win.toggle)

    def on_refresh(icon, item):
        win.root.after(0, lambda: win.refresh(manual=True))

    def on_history(icon, item):
        win.root.after(0, lambda: show_history_popup(win.root))

    def on_quit(icon, item):
        icon.stop()
        win.root.after(0, win.root.quit)

    menu = pystray.Menu(
        pystray.MenuItem("Show / Hide", on_toggle, default=True),
        pystray.MenuItem("Refresh now", on_refresh),
        pystray.MenuItem("History", on_history),
        pystray.MenuItem("Quit", on_quit),
    )
    icon = pystray.Icon("homechecker", make_icon_image(False), "Home Checker", menu)
    win.tray_icon = icon

    threading.Thread(target=icon.run, daemon=True).start()
    win.run()


if __name__ == "__main__":
    main()