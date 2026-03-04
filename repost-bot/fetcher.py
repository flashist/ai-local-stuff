"""
Build a TelegramPost from one or more forwarded Telegram messages.
Media is downloaded via the Bot API — no Telethon / API credentials needed.
"""
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from telegram import Bot, Message


@dataclass
class TelegramPost:
    text: str
    media_paths: list[str] = field(default_factory=list)
    media_types: list[str] = field(default_factory=list)


async def fetch_from_messages(messages: list[Message], bot: Bot) -> TelegramPost:
    """Extract text and download media from a list of messages (single or album)."""
    messages = sorted(messages, key=lambda m: m.message_id)

    # Use text/caption from the first message that has one
    text = ""
    for msg in messages:
        t = msg.text or msg.caption or ""
        if t:
            text = t
            break

    media_dir = Path(tempfile.mkdtemp(prefix="tg_repost_"))
    media_paths: list[str] = []
    media_types: list[str] = []

    for msg in messages:
        path, mtype = await _download_media(msg, bot, media_dir)
        if path:
            media_paths.append(path)
            media_types.append(mtype)

    return TelegramPost(text=text, media_paths=media_paths, media_types=media_types)


async def _download_media(
    msg: Message, bot: Bot, dest_dir: Path
) -> tuple[Optional[str], str]:
    if msg.photo:
        photo = msg.photo[-1]  # largest size
        file = await bot.get_file(photo.file_id)
        path = str(dest_dir / f"{photo.file_id}.jpg")
        await file.download_to_drive(path)
        return path, "photo"

    if msg.video:
        video = msg.video
        ext = (video.mime_type or "video/mp4").split("/")[-1]
        file = await bot.get_file(video.file_id)
        path = str(dest_dir / f"{video.file_id}.{ext}")
        await file.download_to_drive(path)
        return path, "video"

    if msg.document:
        doc = msg.document
        mime = doc.mime_type or ""
        if mime.startswith("video/"):
            ext = mime.split("/")[-1]
            file = await bot.get_file(doc.file_id)
            path = str(dest_dir / f"{doc.file_id}.{ext}")
            await file.download_to_drive(path)
            return path, "video"

    return None, "unknown"
