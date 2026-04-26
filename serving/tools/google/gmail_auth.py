from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CREDENTIALS_PATH = Path(os.getenv("GOOGLE_CREDENTIALS_PATH", str(PROJECT_ROOT / "credentials.json")))
TOKEN_PATH = Path(os.getenv("GOOGLE_TOKEN_PATH", str(PROJECT_ROOT / "state" / "gmail_token.json")))

# gmail.modify covers search/read/label/archive/trash. gmail.send is required for sending drafts.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_credentials() -> Credentials:
    creds: Credentials | None = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"Google OAuth credentials file not found: {CREDENTIALS_PATH}. "
                "Download credentials.json from Google Cloud Console and place it at the project root, "
                "or set GOOGLE_CREDENTIALS_PATH."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def get_gmail_service():
    return build("gmail", "v1", credentials=get_credentials(), cache_discovery=False)
