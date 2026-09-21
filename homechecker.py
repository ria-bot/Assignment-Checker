import sys
from auth_manager import AuthManager
from auth_gui import run_onboarding_gui
from check_elearning import show_elearning_sticky
from check_homework import show_classroom_sticky


def main():
    auth = AuthManager()
    session = auth.load_session()

    # Check if session has both valid eLearning and Google tokens
    has_moodle = bool(session.get("moodle"))
    has_google = bool(auth.get_valid_google_credentials())

    if not has_moodle or not has_google:
        print("Missing or expired credentials. Opening setup wizard...")
        run_onboarding_gui()
        
        # Re-verify session after wizard closes
        session = auth.load_session()
        has_moodle = bool(session.get("moodle"))
        has_google = bool(auth.get_valid_google_credentials())
        
        if not has_moodle or not has_google:
            print("Setup was not completed. Exiting.")
            sys.exit(0)

    # Launch assignment sticky note view
    print("Launching Strathmore Assignment Hub...")
    show_elearning_sticky()
    show_classroom_sticky()


if __name__ == "__main__":
    main()