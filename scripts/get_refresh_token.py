"""
One-time script to obtain a YouTube API refresh token.

Instructions:
1. Ensure you have created an OAuth 2.0 Desktop application in Google Cloud Console.
2. Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in your environment or .env file.
3. Run this script: python scripts/get_refresh_token.py
4. A browser window will open. Log in with the account representing your YouTube channel 
   and grant the requested permissions.
5. The script will print your refresh token.
6. Copy the token and paste it into your GitHub repository secrets under the name: YOUTUBE_REFRESH_TOKEN
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET must be set in the environment or .env file.")
    exit(1)

# YouTube scopes required for uploading videos and setting thumbnails
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

def main() -> None:
    # Create the client configuration dictionary mapping directly to what the flow expects
    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    print("Starting local server for authentication...")
    try:
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        credentials = flow.run_local_server(port=0)

        print("\n" + "="*50)
        print("Authentication Successful!")
        print("Refresh Token:")
        print(credentials.refresh_token)
        print("="*50)
        print("\nPlease copy the refresh token above and add it as a GitHub Repository Secret")
        print("with the exact name: YOUTUBE_REFRESH_TOKEN")
    except Exception as e:
        print(f"\nAuthentication failed: {e}")

if __name__ == "__main__":
    main()
