import datetime
import os
import tkinter as tk
from pathlib import Path
from googleapiclient.discovery import build
from auth_manager import AuthManager


os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

BASE_DIR = Path(__file__).resolve().parent


def get_google_classroom_service():
    """Initializes Google Classroom service using valid session credentials."""
    auth = AuthManager()
    creds = auth.get_valid_google_credentials()
    if not creds:
        raise PermissionError("Google Account is not connected or token expired.")
    return build('classroom', 'v1', credentials=creds)


def get_classroom_assignments_due_today():
    """Fetches Google Classroom assignments due today for the student."""
    service = get_google_classroom_service()
    
    # 1. Fetch active courses
    courses_result = service.courses().list(studentId='me', courseStates=['ACTIVE']).execute()
    courses = courses_result.get('courses', [])
    
    today = datetime.datetime.now(datetime.timezone.utc).date()
    assignments_due = []

    for course in courses:
        course_id = course['id']
        course_name = course['name']
        
        # 2. Fetch coursework
        work_result = service.courses().courseWork().list(courseId=course_id).execute()
        coursework = work_result.get('courseWork', [])

        for item in coursework:
            due_date_dict = item.get('dueDate')
            if not due_date_dict:
                continue
                
            item_date = datetime.date(
                due_date_dict.get('year'),
                due_date_dict.get('month'),
                due_date_dict.get('day')
            )
            
            if item_date == today:
                # 3. Check student submission state
                submissions_result = service.courses().courseWork().studentSubmissions().list(
                    courseId=course_id, courseWorkId=item['id'], studentId='me'
                ).execute()
                
                submissions = submissions_result.get('studentSubmissions', [])
                submitted = False
                if submissions:
                    state = submissions[0].get('state')
                    if state in ['TURNED_IN', 'RETURNED']:
                        submitted = True
                        
                assignments_due.append((course_name, item.get('title', 'Untitled'), submitted))

    return assignments_due


def show_classroom_sticky():
    try:
        assignments = get_classroom_assignments_due_today()
        error = None
    except Exception as e:
        assignments, error = [], str(e)

    root = tk.Tk()
    root.title("Google Classroom")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#FFF8D6")  # Light yellow sticky note

    width, height = 340, 260
    screen_w = root.winfo_screenwidth()
    root.geometry(f"{width}x{height}+{screen_w - width - 30}+60")

    ui_font = ("Cantarell", 10) if os.name != "nt" else ("Segoe UI", 10)
    bold_font = (ui_font[0], 10, "bold")
    header_font = (ui_font[0], 12, "bold")

    header = tk.Label(
        root, text="📌 Google Classroom — Due Today",
        bg="#FFF8D6", fg="#332200",
        font=header_font, anchor="w", padx=10, pady=6
    )
    header.pack(fill="x")

    today_str = datetime.datetime.now().strftime("%A, %d %b %Y")
    tk.Label(
        root, text=today_str, bg="#FFF8D6", fg="#776644",
        font=(ui_font[0], 9), anchor="w", padx=10
    ).pack(fill="x")

    tk.Frame(root, bg="#E6D89A", height=1).pack(fill="x", pady=6)

    body = tk.Frame(root, bg="#FFF8D6")
    body.pack(fill="both", expand=True, padx=10)

    if error:
        tk.Label(
            body, text=f"Error:\n{error}",
            bg="#FFF8D6", fg="#900",
            font=(ui_font[0], 9), wraplength=310, justify="left"
        ).pack(anchor="w")
    elif not assignments:
        tk.Label(
            body, text="Nothing due today.\nYou're clear! ✨",
            bg="#FFF8D6", fg="#332200",
            font=ui_font, justify="left"
        ).pack(anchor="w", pady=8)
    else:
        for course_name, title, submitted in assignments:
            mark = "✅" if submitted else "❌"
            tk.Label(
                body, text=f"{mark} {title}",
                bg="#FFF8D6", fg="#332200",
                font=bold_font, wraplength=310, justify="left", anchor="w"
            ).pack(anchor="w", pady=(4, 0))
            tk.Label(
                body, text=course_name, bg="#FFF8D6", fg="#776644",
                font=(ui_font[0], 8), anchor="w"
            ).pack(anchor="w")

    close = tk.Label(
        root, text="✕", bg="#FFF8D6", fg="#776644",
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
    show_classroom_sticky()