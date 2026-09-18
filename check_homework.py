import os
import datetime
import tkinter as tk
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE_DIR = r"C:\Users\glori\OneDrive\Documents\GitHub\Assignment Checker"
CREDS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

SCOPES = [
    'https://www.googleapis.com/auth/classroom.student-submissions.me.readonly',
    'https://www.googleapis.com/auth/classroom.courses.readonly'
]

LOCAL_TZ_OFFSET = datetime.timedelta(hours=3)  # Kenya


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds


def get_assignments():
    """Returns (due_today_list, not_submitted_list)."""
    creds = get_credentials()
    service = build('classroom', 'v1', credentials=creds)

    courses = service.courses().list(courseStates='ACTIVE').execute().get('courses', [])

    local_now = datetime.datetime.now(datetime.timezone.utc) + LOCAL_TZ_OFFSET
    today_local = local_now.date()

    due_today = []
    not_submitted = []

    for course in courses:
        course_id = course['id']
        course_name = course['name']

        works = service.courses().courseWork().list(
            courseId=course_id,
            courseWorkStates='PUBLISHED'
        ).execute().get('courseWork', [])

        for work in works:
            if 'dueDate' not in work:
                continue

            dd = work['dueDate']
            dt = work.get('dueTime', {'hours': 23, 'minutes': 59})
            due_utc = datetime.datetime(
                dd['year'], dd['month'], dd['day'],
                dt.get('hours', 23), dt.get('minutes', 59),
                tzinfo=datetime.timezone.utc
            )
            due_local = due_utc + LOCAL_TZ_OFFSET

            if due_local.date() != today_local:
                continue

            title = work['title']
            due_today.append((title, course_name))

            subs = service.courses().courseWork().studentSubmissions().list(
                courseId=course_id,
                courseWorkId=work['id'],
                userId='me'
            ).execute().get('studentSubmissions', [])

            state = subs[0].get('state') if subs else 'NEW'
            if state not in ('TURNED_IN', 'RETURNED'):
                not_submitted.append((title, course_name))

    return due_today, not_submitted


def show_sticky_note():
    try:
        due_today, not_submitted = get_assignments()
        error = None
    except Exception as e:
        due_today, not_submitted, error = [], [], str(e)

    root = tk.Tk()
    root.title("Assignments")
    root.overrideredirect(True)          # remove title bar
    root.attributes("-topmost", True)    # stay above other windows
    root.configure(bg="#DB8797")         # sticky-note yellow

    # Position: top-right corner
    width, height = 270, 360
    screen_w = root.winfo_screenwidth()
    root.geometry(f"{width}x{height}+{screen_w - width - 30}+60")

    # Header
    header = tk.Label(
        root, text="📌 Due Today",
        bg="#C17B9C", fg="#333",
        font=("Segoe UI", 12, "bold"),
        anchor="w", padx=10, pady=6
    )
    header.pack(fill="x")

    # Date line
    today_str = datetime.datetime.now().strftime("%A, %d %b %Y")
    tk.Label(
        root, text=today_str,
        bg="#DB8797", fg="#666",
        font=("Segoe UI", 9),
        anchor="w", padx=10
    ).pack(fill="x")

    tk.Frame(root, bg="#C17B9C", height=1).pack(fill="x", pady=6)

    # Body
    body = tk.Frame(root, bg="#DB8797")
    body.pack(fill="both", expand=True, padx=10)

    if error:
        tk.Label(
            body, text=f"Error:\n{error}",
            bg="#DB8797", fg="#900",
            font=("Segoe UI", 9), wraplength=290, justify="left"
        ).pack(anchor="w")
    elif not due_today:
        tk.Label(
            body, text="Nothing due today.\nYou're clear! ✨",
            bg="#DB8797", fg="#333",
            font=("Segoe UI", 10), justify="left"
        ).pack(anchor="w", pady=8)
    else:
        for title, course in due_today:
            submitted = all(t != title for t, _ in not_submitted)
            mark = "✅" if submitted else "❌"
            tk.Label(
                body, text=f"{mark} {title}",
                bg="#DB8797", fg="#222",
                font=("Segoe UI", 10, "bold"),
                wraplength=290, justify="left", anchor="w"
            ).pack(anchor="w", pady=(4, 0))
            tk.Label(
                body, text=course,
                bg="#DB8797", fg="#777",
                font=("Segoe UI", 8),
                anchor="w"
            ).pack(anchor="w")

    # Close button
    close = tk.Label(
        root, text="✕", bg="#DB8797", fg="#666",
        font=("Segoe UI", 11, "bold"), cursor="hand2"
    )
    close.place(relx=1.0, y=4, x=-10, anchor="ne")
    close.bind("<Button-1>", lambda e: root.destroy())

    # Drag anywhere on the note
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


if __name__ == '__main__':
    show_sticky_note()