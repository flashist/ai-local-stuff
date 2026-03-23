"""
Telegram bot entry point.

Two ways to trigger a repost:

1. Forward a post from your channel to the bot.
2. Send a video (or document) directly to the bot with the post text as the caption.
   Use /post to trigger — the bot waits for you to attach a video + caption.
"""
import asyncio
import logging
import os
import shutil
from collections import defaultdict

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import fetcher
import transformer
import vk_poster
import ig_poster

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# Album buffering: group forwarded messages that share a media_group_id
_album_buffers: dict[str, list] = defaultdict(list)
_album_tasks: dict[str, asyncio.Task] = {}
_ALBUM_WAIT = 1.5  # seconds to wait for all album parts to arrive

# Users who have issued /post and are waiting to send a video
_awaiting_direct_post: set[int] = set()


def _auth_check(user_id: int) -> bool:
    return user_id == config.TELEGRAM_ALLOWED_USER_ID


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _auth_check(update.effective_user.id):
        return
    await update.message.reply_text(
        "Hi! Two ways to repost:\n\n"
        "1. Forward a channel post to me.\n"
        "2. Send /post — then attach a video with the caption as your post text."
    )


async def cmd_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _auth_check(update.effective_user.id):
        return
    _awaiting_direct_post.add(update.effective_user.id)
    await update.message.reply_text(
        "Ready. Send me a video (or file) with the post text as the caption."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _auth_check(update.effective_user.id):
        return

    message = update.effective_message
    user_id = update.effective_user.id

    # --- Direct post mode: user sent /post and is now sending a video ---
    if user_id in _awaiting_direct_post and (message.video or message.document):
        _awaiting_direct_post.discard(user_id)
        await _repost(message, [message], context)
        return

    # --- Forwarded channel post ---
    if not message.forward_origin:
        await message.reply_text(
            "Please forward a channel post, or use /post to send a video directly."
        )
        return

    media_group_id = message.media_group_id

    if media_group_id:
        # Album: buffer messages and wait for all parts to arrive
        _album_buffers[media_group_id].append(message)

        # Reset the timer each time a new part arrives
        if media_group_id in _album_tasks:
            _album_tasks[media_group_id].cancel()

        async def process_album(mgid: str = media_group_id) -> None:
            await asyncio.sleep(_ALBUM_WAIT)
            messages = _album_buffers.pop(mgid, [])
            _album_tasks.pop(mgid, None)
            if messages:
                await _repost(messages[0], messages, context)

        _album_tasks[media_group_id] = asyncio.create_task(process_album())
    else:
        await _repost(message, [message], context)


async def _repost(
    reply_to,  # message to reply status updates to
    messages: list,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    status_msg = await reply_to.reply_text("Fetching content...")

    try:
        post = await fetcher.fetch_from_messages(messages, context.bot)
    except Exception as exc:
        log.exception("Fetch failed")
        await status_msg.edit_text(f"Failed to read post:\n{exc}")
        return

    media_info = ""
    for path, mtype in zip(post.media_paths, post.media_types):
        size_mb = os.path.getsize(path) / 1024 / 1024
        media_info += f"\n  {mtype}: {size_mb:.1f} MB → {path}"

    await status_msg.edit_text(
        f"Fetched: {len(post.text)} chars, {len(post.media_paths)} media file(s).{media_info}\n\n"
        "Posting to VK and Instagram..."
    )

    results: list[str] = []

    # --- VK ---
    try:
        vk_text = transformer.transform(post.text, "vk")
        vk_url = vk_poster.post_to_vk(post, vk_text)
        results.append(f"VK: {vk_url}")
        log.info("Posted to VK: %s", vk_url)
    except Exception as exc:
        log.exception("VK posting failed")
        results.append(f"VK: FAILED — {exc}")

    # --- Instagram ---
    try:
        ig_text = transformer.transform(post.text, "instagram")
        ig_url = ig_poster.post_to_instagram(post, ig_text)
        results.append(f"Instagram: {ig_url}")
        log.info("Posted to Instagram: %s", ig_url)
    except Exception as exc:
        log.exception("Instagram posting failed")
        results.append(f"Instagram: FAILED — {exc}")

    # Cleanup temp media files
    dirs_to_remove = {str(p).rsplit("/", 1)[0] for p in post.media_paths}
    for d in dirs_to_remove:
        shutil.rmtree(d, ignore_errors=True)

    await status_msg.edit_text("Done!\n\n" + "\n".join(results))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("post", cmd_post))
    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.FORWARDED | filters.CAPTION | filters.PHOTO | filters.VIDEO | filters.Document.VIDEO,
            handle_message,
        )
    )

    log.info("Bot started. Waiting for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
