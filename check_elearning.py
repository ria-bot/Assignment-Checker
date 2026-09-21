import datetime
import os
import tkinter as tk
from pathlib import Path
import requests
from auth_manager import AuthManager

BASE_DIR = Path(__file__).resolve().parent
MOODLE_URL = "https://elearning.strathmore.edu/webservice/rest/server.php"
LOCAL_TZ_OFFSET = datetime.timedelta(hours=3)  # Kenya (EAT)


def get_moodle_token() -> str:
    """Loads the decrypted Moodle web service token from the active session."""
    auth = AuthManager()
    session = auth.load_session()
    token = session.get("moodle")
    if not token:
        raise FileNotFoundError("No active eLearning session found. Please log in first.")
    return token


def call_moodle(token: str, function: str, **params) -> dict | list:
    """Generic Moodle REST API call."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) StrathmoreAssignmentHub/1.0"
    }
    query = {
        "wstoken": token,
        "wsfunction": function,
        "moodlewsrestformat": "json",
    }
    query.update(params)
    
    response = requests.get(MOODLE_URL, params=query, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    if isinstance(data, dict) and data.get("exception"):
        raise RuntimeError(data.get("message", "Moodle API Error"))
        
    return data


def get_user_id(token: str) -> int:
    """Dynamically retrieves authenticated user's numeric ID from Moodle."""
    site_info = call_moodle(token, "core_webservice_get_site_info")
    if "userid" in site_info:
        return site_info["userid"]
    raise ValueError("Could not retrieve user ID from site info.")


def get_assignments_due_today(token: str) -> list[tuple[str, str, bool]]:
    """Returns list of (course_name, assignment_name, submitted_bool) for today."""
    user_id = get_user_id(token)

    local_now = datetime.datetime.now(datetime.timezone.utc) + LOCAL_TZ_OFFSET
    today_start = datetime.datetime.combine(local_now.date(), datetime.time.min)
    today_end = today_start + datetime.timedelta(days=1)

    start_ts = int((today_start - LOCAL_TZ_OFFSET).timestamp())
    end_ts = int((today_end - LOCAL_TZ_OFFSET).timestamp())

    courses = call_moodle(token, "core_enrol_get_users_courses", userid=user_id)
    results = []

    for course in courses:
        course_id = course["id"]
        course_name = course["fullname"]

        data = call_moodle(
            token, "mod_assign_get_assignments", **{"courseids[0]": course_id}
        )
        if not isinstance(data, dict) or "courses" not in data:
            continue

        for c in data["courses"]:
            for a in c.get("assignments", []):
                due = a.get("duedate", 0)
                if not due or not (start_ts <= due < end_ts):
                    continue

                sub = call_moodle(
                    token,
                    "mod_assign_get_submissions",
                    **{"assignmentids[0]": a["id"]}
                )
                submitted = False
                try:
                    for s_course in sub.get("assignments", []):
                        for s in s_course.get("submissions", []):
                            if s.get("userid") == user_id:
                                if s.get("status") == "submitted":
                                    submitted = True
                except Exception:
                    pass

                results.append((course_name, a["name"], submitted))

    return results


def show_elearning_sticky():
    try:
        token = get_moodle_token()
        assignments = get_assignments_due_today(token)
        error = None
    except Exception as e:
        assignments, error = [], str(e)

    root = tk.Tk()
    root.title("eLearning")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#D8ECFF")

    width, height = 340, 280
    screen_w = root.winfo_screenwidth()
    root.geometry(f"{width}x{height}+{screen_w - width - 30}+340")

    ui_font = ("Cantarell", 10) if os.name != "nt" else ("Segoe UI", 10)
    bold_font = (ui_font[0], 10, "bold")
    header_font = (ui_font[0], 12, "bold")

    header = tk.Label(
        root, text="📚 eLearning — Due Today",
        bg="#D8ECFF", fg="#123",
        font=header_font, anchor="w", padx=10, pady=6
    )
    header.pack(fill="x")

    today_str = datetime.datetime.now().strftime("%A, %d %b %Y")
    tk.Label(
        root, text=today_str, bg="#D8ECFF", fg="#567",
        font=(ui_font[0], 9), anchor="w", padx=10
    ).pack(fill="x")

    tk.Frame(root, bg="#A8C8E8", height=1).pack(fill="x", pady=6)

    body = tk.Frame(root, bg="#D8ECFF")
    body.pack(fill="both", expand=True, padx=10)

    if error:
        tk.Label(
            body, text=f"Error:\n{error}",
            bg="#D8ECFF", fg="#900",
            font=(ui_font[0], 9), wraplength=310, justify="left"
        ).pack(anchor="w")
    elif not assignments:
        tk.Label(
            body, text="Nothing due today.\nYou're clear! ✨",
            bg="#D8ECFF", fg="#234",
            font=ui_font, justify="left"
        ).pack(anchor="w", pady=8)
    else:
        for course_name, title, submitted in assignments:
            mark = "✅" if submitted else "❌"
            tk.Label(
                body, text=f"{mark} {title}",
                bg="#D8ECFF", fg="#123",
                font=bold_font, wraplength=310, justify="left", anchor="w"
            ).pack(anchor="w", pady=(4, 0))
            tk.Label(
                body, text=course_name, bg="#D8ECFF", fg="#678",
                font=(ui_font[0], 8), anchor="w"
            ).pack(anchor="w")

    close = tk.Label(
        root, text="✕", bg="#D8ECFF", fg="#567",
        font=(ui_font[0], 11, "bold"), cursor="hand2"
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
    show_elearning_sticky()