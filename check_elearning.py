import os
import datetime
import tkinter as tk
import urllib.parse
import urllib.request
import json

BASE_DIR = r"C:\Users\glori\OneDrive\Documents\GitHub\Assignment Checker"
TOKEN_FILE = os.path.join(BASE_DIR, "moodle_token.txt")

MOODLE_URL = "https://elearning.strathmore.edu/webservice/rest/server.php"
USERID = 57548
LOCAL_TZ_OFFSET = datetime.timedelta(hours=3)  # Kenya


def load_token():
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def call_moodle(token, function, **params):
    """Generic Moodle REST call."""
    query = {
        "wstoken": token,
        "wsfunction": function,
        "moodlewsrestformat": "json",
    }
    query.update(params)
    url = MOODLE_URL + "?" + urllib.parse.urlencode(query)
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def get_assignments_due_today(token):
    """Returns list of (course_name, assignment_name, submitted_bool) for today."""
    local_now = datetime.datetime.now(datetime.timezone.utc) + LOCAL_TZ_OFFSET
    today_start = datetime.datetime.combine(local_now.date(), datetime.time.min)
    today_end = today_start + datetime.timedelta(days=1)

    # Convert to UTC unix timestamps (Moodle uses UTC)
    start_ts = int((today_start - LOCAL_TZ_OFFSET).timestamp())
    end_ts = int((today_end - LOCAL_TZ_OFFSET).timestamp())

    # 1. Get enrolled courses
    courses = call_moodle(token, "core_enrol_get_users_courses", userid=USERID)
    if isinstance(courses, dict) and courses.get("exception"):
        raise RuntimeError(courses.get("message", "Moodle error"))

    results = []

    for course in courses:
        course_id = course["id"]
        course_name = course["fullname"]

        # 2. Get assignments in this course
        data = call_moodle(
            token, "mod_assign_get_assignments", **{"courseids[0]": course_id}
        )
        if not isinstance(data, dict) or "courses" not in data:
            continue

        for c in data["courses"]:
            for a in c.get("assignments", []):
                due = a.get("duedate", 0)
                if not due:
                    continue
                if not (start_ts <= due < end_ts):
                    continue

                # 3. Check submission state
                sub = call_moodle(
                    token,
                    "mod_assign_get_submissions",
                    **{"assignmentids[0]": a["id"]}
                )
                submitted = False
                try:
                    for s_course in sub.get("assignments", []):
                        for s in s_course.get("submissions", []):
                            if s.get("userid") == USERID:
                                status = s.get("status", "")
                                if status == "submitted":
                                    submitted = True
                except Exception:
                    pass

                results.append((course_name, a["name"], submitted))

    return results


def show_sticky_note():
    try:
        token = load_token()
        assignments = get_assignments_due_today(token)
        error = None
    except Exception as e:
        assignments, error = [], str(e)

    root = tk.Tk()
    root.title("eLearning")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#D8ECFF")  # light blue to distinguish from Classroom

    width, height = 340, 280
    screen_w = root.winfo_screenwidth()
    # Place it below the Classroom sticky (which is at +60)
    root.geometry(f"{width}x{height}+{screen_w - width - 30}+340")

    header = tk.Label(
        root, text="📚 eLearning — Due Today",
        bg="#D8ECFF", fg="#123",
        font=("Segoe UI", 12, "bold"),
        anchor="w", padx=10, pady=6
    )
    header.pack(fill="x")

    today_str = datetime.datetime.now().strftime("%A, %d %b %Y")
    tk.Label(
        root, text=today_str, bg="#D8ECFF", fg="#567",
        font=("Segoe UI", 9), anchor="w", padx=10
    ).pack(fill="x")

    tk.Frame(root, bg="#A8C8E8", height=1).pack(fill="x", pady=6)

    body = tk.Frame(root, bg="#D8ECFF")
    body.pack(fill="both", expand=True, padx=10)

    if error:
        tk.Label(
            body, text=f"Error:\n{error}",
            bg="#D8ECFF", fg="#900",
            font=("Segoe UI", 9), wraplength=310, justify="left"
        ).pack(anchor="w")
    elif not assignments:
        tk.Label(
            body, text="Nothing due today.\nYou're clear! ✨",
            bg="#D8ECFF", fg="#234",
            font=("Segoe UI", 10), justify="left"
        ).pack(anchor="w", pady=8)
    else:
        for course_name, title, submitted in assignments:
            mark = "✅" if submitted else "❌"
            tk.Label(
                body, text=f"{mark} {title}",
                bg="#D8ECFF", fg="#123",
                font=("Segoe UI", 10, "bold"),
                wraplength=310, justify="left", anchor="w"
            ).pack(anchor="w", pady=(4, 0))
            tk.Label(
                body, text=course_name, bg="#D8ECFF", fg="#678",
                font=("Segoe UI", 8), anchor="w"
            ).pack(anchor="w")

    close = tk.Label(
        root, text="✕", bg="#D8ECFF", fg="#567",
        font=("Segoe UI", 11, "bold"), cursor="hand2"
    )
    close.place(relx=1.0, y=4, x=-10, anchor="ne")
    close.bind("<Button-1>", lambda e: root.destroy())

    def start_move(event):
        root.x = event.x
        root.y = event.y

    def do_move(event):
        x = event.x_root - root.x
        y = event.y_root - root.y
        root.geometry(f"+{x}+{y}")

    for widget in (root, header):
        widget.bind("<Button-1>", start_move)
        widget.bind("<B1-Motion>", do_move)

    root.mainloop()


if __name__ == "__main__":
    show_sticky_note()