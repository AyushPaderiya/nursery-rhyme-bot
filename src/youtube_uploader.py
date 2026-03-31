"""YouTube uploader module for the Nursery Rhyme Bot pipeline.

Uploads the assembled video and thumbnail to YouTube via the
YouTube Data API v3 with correct Kids content metadata
(madeForKids: True, selfDeclaredMadeForKids: True).
"""

import os
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.utils import load_env, retry, iso_now


@retry(max_attempts=3, backoff_factor=2)
def get_youtube_service() -> Any:
    """Build an authenticated YouTube Data API v3 service.

    Uses OAuth2 refresh token flow with credentials from environment
    variables: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN.

    Returns:
        An authenticated googleapiclient.discovery.Resource for YouTube.
    """
    client_id = load_env("YOUTUBE_CLIENT_ID")
    client_secret = load_env("YOUTUBE_CLIENT_SECRET")
    refresh_token = load_env("YOUTUBE_REFRESH_TOKEN")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    return build("youtube", "v3", credentials=creds)


@retry(max_attempts=3, backoff_factor=2)
def upload_video(video_path: str, thumbnail_path: str, script: dict) -> dict[str, Any]:
    """Upload a video to YouTube with Kids-safe metadata.

    IMPORTANT: madeForKids and selfDeclaredMadeForKids are ALWAYS True.
    The seo_title is truncated to 100 characters maximum.

    Args:
        video_path: Path to the MP4 video file.
        thumbnail_path: Path to the thumbnail JPEG file.
        script: RhymeScript dictionary.

    Returns:
        UploadResult dictionary with video_id, video_url, thumbnail_set.
    """
    service = get_youtube_service()

    title = script["seo_title"]
    if len(title) > 100:
        # Truncate at last space before 97 chars to avoid mid-word cut
        truncated = title[:97]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            title = truncated[:last_space] + "..."
        else:
            title = truncated + "..."

    body = {
        "snippet": {
            "title": title,
            "description": script["description"],
            "tags": script["tags"],
            "categoryId": "22",
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en"
        },
        "status": {
            "privacyStatus": "public",
            "madeForKids": True,
            "selfDeclaredMadeForKids": True
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[uploader] Uploaded {int(status.progress() * 100)}%")

    video_id = response["id"]
    video_url = f"https://youtu.be/{video_id}"
    print(f"[uploader] Video uploaded! ID: {video_id}")

    # Set thumbnail
    thumbnail_media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
    service.thumbnails().set(
        videoId=video_id,
        media_body=thumbnail_media
    ).execute()
    
    print(f"[uploader] Thumbnail set for {video_id}")

    return {
        "video_id": video_id,
        "video_url": video_url,
        "thumbnail_set": True
    }


if __name__ == "__main__":
    print("youtube_uploader.py loaded ✓")
