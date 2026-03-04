"""
Telegram bot entry point.

Usage: forward any post from your channel to this bot.

The bot will:
  1. Collect all messages in the forwarded post (handles albums)
  2. Apply platform-specific text substitutions
  3. Post to VK and Instagram
  4. Reply with status + links
"""
import asyncio
import logging
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


def _auth_check(user_id: int) -> bool:
    return user_id == config.TELEGRAM_ALLOWED_USER_ID


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _auth_check(update.effective_user.id):
        return
    await update.message.reply_text(
        "Hi! Forward any post from your channel and I'll repost it to VK and Instagram."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _auth_check(update.effective_user.id):
        return

    message = update.effective_message

    if not message.forward_origin:
        await message.reply_text("Please forward a channel post to me.")
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

    await status_msg.edit_text(
        f"Fetched: {len(post.text)} chars, {len(post.media_paths)} media file(s).\n"
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
    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.FORWARDED | filters.CAPTION | filters.PHOTO | filters.VIDEO,
            handle_message,
        )
    )

    log.info("Bot started. Waiting for forwarded messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
