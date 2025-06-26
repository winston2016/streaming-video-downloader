import os
from instagrapi import Client


def upload_video(path: str, caption: str = ""):
    """Upload a video to Instagram using instagrapi."""
    user = os.getenv("INSTAGRAM_USER")
    password = os.getenv("INSTAGRAM_PASSWORD")
    if not user or not password:
        raise RuntimeError("Instagram credentials not configured")
    cl = Client()
    cl.login(user, password)
    cl.clip_upload(path, caption)
