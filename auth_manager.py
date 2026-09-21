import os
import json
import keyring
import requests
from pathlib import Path
from cryptography.fernet import Fernet
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "user_data.enc"

from dotenv import load_dotenv

load_dotenv()

# Embedded Public Google Client Configuration for Desktop OAuth
GOOGLE_CLIENT_CONFIG = {
    "installed": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "project_id": "strathmore-assignment-hub",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris": ["http://localhost"]
    }
}

# In auth_manager.py

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.students.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly"
]

SERVICE_NAME = "StrathmoreAssignmentHub"
KEYRING_USER = "local_app_key"

MOODLE_LOGIN_URL = "https://elearning.strathmore.edu/login/token.php"


class AuthManager:
    def __init__(self):
        self.fernet = self._get_or_create_cipher()

    def _get_or_create_cipher(self) -> Fernet:
        """Retrieves or generates an encryption key stored inside system keyring."""
        secret_key = keyring.get_password(SERVICE_NAME, KEYRING_USER)
        if not secret_key:
            secret_key = Fernet.generate_key().decode("utf-8")
            keyring.set_password(SERVICE_NAME, KEYRING_USER, secret_key)
        return Fernet(secret_key.encode("utf-8"))

    def save_session(self, session_data: dict):
        """Encrypts and writes session data to local disk."""
        json_bytes = json.dumps(session_data).encode("utf-8")
        encrypted_bytes = self.fernet.encrypt(json_bytes)
        DATA_FILE.write_bytes(encrypted_bytes)

    def load_session(self) -> dict:
        """Loads and decrypts local session data."""
        if not DATA_FILE.exists():
            return {}
        try:
            encrypted_bytes = DATA_FILE.read_bytes()
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_bytes.decode("utf-8"))
        except Exception as e:
            print(f"Failed to load session ({e}). Resetting storage.")
            self.clear_session()
            return {}

    def clear_session(self):
        """Clears local encrypted session storage."""
        if DATA_FILE.exists():
            DATA_FILE.unlink(missing_ok=True)

    # --- MOODLE AUTHENTICATION --- #
    def authenticate_moodle(self, username, password) -> str:
        """Exchanges username and password for a Moodle web service token."""
        payload = {
            "username": username,
            "password": password,
            "service": "moodle_mobile_app"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) StrathmoreAssignmentHub/1.0"
        }
        
        response = requests.post(MOODLE_LOGIN_URL, data=payload, headers=headers, timeout=12)
        response.raise_for_status()
        data = response.json()

        if "token" in data:
            return data["token"]
        elif "error" in data:
            raise ValueError(data.get("error"))
        else:
            raise ValueError("Invalid eLearning credentials provided.")

    # --- GOOGLE OAUTH --- #
    def authenticate_google(self) -> dict:
        """Launches PKCE browser OAuth flow enforced for @strathmore.edu domain."""
        flow = InstalledAppFlow.from_client_config(
            GOOGLE_CLIENT_CONFIG,
            scopes=SCOPES
        )
        
        # Enforce Strathmore email domain prompt
        creds = flow.run_local_server(
            port=0,
            authorization_prompt_message="Opening browser for Strathmore Google authorization...",
            success_message="Authorization successful! You can close this window now.",
            hd="strathmore.edu"
        )
        return json.loads(creds.to_json())

    def get_valid_google_credentials(self) -> Credentials | None:
        """Returns active Google Credentials object, refreshing automatically if expired."""
        session = self.load_session()
        google_data = session.get("google")
        
        if not google_data:
            return None

        creds = Credentials.from_authorized_user_info(google_data, SCOPES)
        
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed credentials state back to disk
            session["google"] = json.loads(creds.to_json())
            self.save_session(session)
            
        return creds if creds.valid else None


if __name__ == "__main__":
    # Internal module testing
    auth = AuthManager()
    print("Encryption engine initialized successfully!")
    print(f"Active Session Exists: {bool(auth.load_session())}")