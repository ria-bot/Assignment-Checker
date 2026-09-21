import os
import tkinter as tk
from tkinter import messagebox
from auth_manager import AuthManager


class OnboardingGUI:
    def __init__(self):
        self.auth = AuthManager()
        self.session_data = self.auth.load_session()
        
        self.root = tk.Tk()
        self.root.title("Strathmore Assignment Hub — Setup")
        self.root.geometry("400x520")
        self.root.resizable(False, False)
        
        # Cross-platform font configuration
        self.ui_font = ("Cantarell", 10) if os.name != "nt" else ("Segoe UI", 10)
        self.title_font = (self.ui_font[0], 14, "bold")
        self.bold_font = (self.ui_font[0], 10, "bold")

        self.root.configure(bg="#F4F6F9")
        self._build_ui()

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#002B49", pady=15)
        header.pack(fill="x")
        
        tk.Label(
            header, text="🎓 Strathmore Assignment Hub",
            fg="white", bg="#002B49", font=self.title_font
        ).pack()
        
        tk.Label(
            header, text="One-time setup for Classroom & eLearning",
            fg="#A8C8E8", bg="#002B49", font=(self.ui_font[0], 9)
        ).pack(pady=(2, 0))

        # Main Container
        container = tk.Frame(self.root, bg="#F4F6F9", padx=20, pady=20)
        container.pack(fill="both", expand=True)

        # Step 1: Google Classroom Auth
        step1_frame = tk.LabelFrame(
            container, text=" Step 1: Strathmore Google Account ",
            bg="#F4F6F9", fg="#002B49", font=self.bold_font, padx=10, pady=10
        )
        step1_frame.pack(fill="x", pady=(0, 15))

        self.google_status_lbl = tk.Label(
            step1_frame, 
            text="Status: Connected" if "google" in self.session_data else "Status: Not Connected",
            fg="#2E7D32" if "google" in self.session_data else "#C62828",
            bg="#F4F6F9", font=self.ui_font
        )
        self.google_status_lbl.pack(anchor="w", pady=(0, 5))

        self.btn_google = tk.Button(
            step1_frame, text="🔐 Sign in with @strathmore.edu",
            bg="#002B49", fg="white", font=self.bold_font,
            activebackground="#004080", activeforeground="white",
            cursor="hand2", command=self._handle_google_signin
        )
        self.btn_google.pack(fill="x")

        # Step 2: eLearning Credentials
        step2_frame = tk.LabelFrame(
            container, text=" Step 2: eLearning Credentials ",
            bg="#F4F6F9", fg="#002B49", font=self.bold_font, padx=10, pady=10
        )
        step2_frame.pack(fill="x")

        tk.Label(step2_frame, text="Student ID / Username:", bg="#F4F6F9", font=self.ui_font).pack(anchor="w")
        self.entry_user = tk.Entry(step2_frame, font=self.ui_font)
        self.entry_user.pack(fill="x", pady=(2, 10))

        tk.Label(step2_frame, text="eLearning Password:", bg="#F4F6F9", font=self.ui_font).pack(anchor="w")
        self.entry_pass = tk.Entry(step2_frame, show="•", font=self.ui_font)
        self.entry_pass.pack(fill="x", pady=(2, 10))

        self.elearning_status_lbl = tk.Label(
            step2_frame,
            text="Status: Connected" if "moodle" in self.session_data else "Status: Not Connected",
            fg="#2E7D32" if "moodle" in self.session_data else "#C62828",
            bg="#F4F6F9", font=self.ui_font
        )
        self.elearning_status_lbl.pack(anchor="w", pady=(0, 5))

        # Finish / Save Button
        self.btn_save = tk.Button(
            container, text="🚀 Complete Setup & Start",
            bg="#2E7D32", fg="white", font=self.bold_font,
            activebackground="#1B5E20", activeforeground="white",
            cursor="hand2", command=self._handle_save
        )
        self.btn_save.pack(fill="x", pady=(20, 0))

    def _handle_google_signin(self):
        try:
            google_creds_dict = self.auth.authenticate_google()
            self.session_data["google"] = google_creds_dict
            self.auth.save_session(self.session_data)
            
            self.google_status_lbl.config(text="Status: Connected", fg="#2E7D32")
            messagebox.showinfo("Success", "Google Account connected successfully!")
        except Exception as e:
            messagebox.showerror("Authentication Error", f"Google sign-in failed:\n{e}")

    def _handle_save(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()

        # Check if Moodle needs connection
        if "moodle" not in self.session_data:
            if not username or not password:
                messagebox.showwarning("Input Required", "Please enter your eLearning Username and Password.")
                return
            
            try:
                moodle_token = self.auth.authenticate_moodle(username, password)
                self.session_data["moodle"] = moodle_token
                self.auth.save_session(self.session_data)
                self.elearning_status_lbl.config(text="Status: Connected", fg="#2E7D32")
            except Exception as e:
                messagebox.showerror("eLearning Error", f"Failed to authenticate with eLearning:\n{e}")
                return

        if "google" not in self.session_data:
            messagebox.showwarning("Google Sign-In Required", "Please connect your @strathmore.edu Google account before proceeding.")
            return

        messagebox.showinfo("Setup Complete", "Setup successful! Launching your Assignment Hub.")
        self.root.destroy()


def run_onboarding_gui():
    app = OnboardingGUI()
    app.root.mainloop()


if __name__ == "__main__":
    run_onboarding_gui()