import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def upload_video(path: str, title: str = "Video", description: str = "", privacy_status: str = "public"):
    """Upload a video to YouTube using OAuth credentials."""
    client_file = os.getenv("YOUTUBE_CLIENT_SECRETS")
    if not client_file:
        raise RuntimeError("YOUTUBE_CLIENT_SECRETS not configured")
    flow = InstalledAppFlow.from_client_secrets_file(client_file, SCOPES)
    creds = flow.run_local_server()
    service = build("youtube", "v3", credentials=creds)
    request = service.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": privacy_status},
        },
        media_body=MediaFileUpload(path)
    )
    request.execute()
