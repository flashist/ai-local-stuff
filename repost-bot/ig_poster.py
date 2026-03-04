"""
Post a video to Instagram via the official Graph API (resumable upload).
"""
import os
import time
import requests

import config
from fetcher import TelegramPost

_IG_BASE = "https://graph.facebook.com/v20.0"


def _upload_video(video_path: str, caption: str) -> str:
    """Upload video via resumable upload and return the container ID."""
    file_size = os.path.getsize(video_path)

    # Step 1: initialise upload session
    init_resp = requests.post(
        f"{_IG_BASE}/{config.INSTAGRAM_USER_ID}/media",
        params={
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "access_token": config.INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    init_resp.raise_for_status()
    init_data = init_resp.json()
    upload_url = init_data["uri"]
    container_id = init_data["id"]

    # Step 2: upload bytes
    with open(video_path, "rb") as f:
        upload_resp = requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {config.INSTAGRAM_ACCESS_TOKEN}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream",
            },
            data=f,
            timeout=300,
        )
    upload_resp.raise_for_status()

    return container_id


def _wait_for_container(container_id: str, max_wait: int = 300) -> None:
    """Poll until container status is FINISHED."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        resp = requests.get(
            f"{_IG_BASE}/{container_id}",
            params={
                "fields": "status_code,status",
                "access_token": config.INSTAGRAM_ACCESS_TOKEN,
            },
            timeout=15,
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram container processing failed: {resp.json()}")
        time.sleep(5)
    raise TimeoutError(f"Container {container_id} not ready after {max_wait}s")


def _publish(container_id: str) -> str:
    """Publish a ready container. Returns the permalink."""
    resp = requests.post(
        f"{_IG_BASE}/{config.INSTAGRAM_USER_ID}/media_publish",
        params={
            "creation_id": container_id,
            "access_token": config.INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    resp.raise_for_status()
    media_id = resp.json()["id"]

    detail = requests.get(
        f"{_IG_BASE}/{media_id}",
        params={
            "fields": "permalink",
            "access_token": config.INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=15,
    )
    detail.raise_for_status()
    return detail.json().get("permalink", f"https://www.instagram.com/p/{media_id}/")


def post_to_instagram(post: TelegramPost, text: str) -> str:
    """Upload the video and publish it as a Reel. Returns the permalink."""
    videos = [p for p, t in zip(post.media_paths, post.media_types) if t == "video"]
    if not videos:
        raise ValueError("No video found in post.")

    container_id = _upload_video(videos[0], text)
    _wait_for_container(container_id)
    return _publish(container_id)
