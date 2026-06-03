"""
auth_youtube_oauth.py
---------------------
One-time OAuth setup for YouTube captions.download access.

Run this once:
    uv run python data/auth_youtube_oauth.py

It opens a browser tab to authenticate with your Google account,
then saves token.json in the project root. The pipeline reuses
this token silently on all future runs.

Requirements:
    - client_secrets.json in the project root
      (download from Google Cloud Console → Credentials → OAuth 2.0 Client ID)
    - uv add google-auth-oauthlib
"""

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLIENT_SECRETS = PROJECT_ROOT / "client_secrets.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def get_credentials():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS.exists():
                print(f"\n❌ client_secrets.json not found at {CLIENT_SECRETS}")
                print("   Download it from: Google Cloud Console → APIs & Services → Credentials")
                print("   → Your OAuth 2.0 Client ID → Download JSON")
                print("   → Save as client_secrets.json in the project root\n")
                return None

            print("\nOpening browser for Google account login...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())
        print(f"\n✓ Token saved to {TOKEN_FILE}")

    return creds


if __name__ == "__main__":
    creds = get_credentials()
    if creds:
        print("✓ OAuth setup complete — token.json is ready.")
        print("  The pipeline will use this automatically from now on.")
