# Repost Bot

A Telegram bot that reposts content from a Telegram channel to **VK** and **Instagram** automatically.

Forward a channel post to the bot → it reposts to both platforms with platform-specific text adjustments.

---

## How it works

1. You forward a post from your Telegram channel to the bot
2. The bot downloads the text and video
3. It applies mention substitutions defined in `mentions.json` (per platform)
4. It posts to your VK community wall and Instagram (as a Reel)
5. It replies to you with the links to the published posts

---

## Requirements

- Python 3.10+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- A VK community + API tokens
- An Instagram Business or Creator account + Meta Graph API access

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set each value (see [Credentials](#credentials) below).

### 3. Configure mention substitutions (optional)

Edit `mentions.json` to define how names/mentions should be rewritten per platform.
If a platform key is absent for a rule, that platform's text is left unchanged.

```json
{
  "substitutions": [
    {
      "match": "John",
      "instagram": "@john_doe"
    },
    {
      "match": "Some Place",
      "vk": "@someplace_vk",
      "instagram": "@someplace.ig"
    }
  ]
}
```

### 4. Run the bot

```bash
python bot.py
```

Once you see `Bot started. Waiting for forwarded messages...`, the bot is ready.

---

## Usage

Open Telegram, find your bot, and **forward any post from your channel** to it.

The bot will reply with status updates and, when done, the links to the new posts on VK and Instagram.

> **Note on video quality:** Telegram compresses videos posted as regular video messages. To preserve original quality, post videos to your channel using **"Send as file"** (Document) instead of as a video.

---

## Credentials

### Telegram

| Variable | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Create a bot via [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_ALLOWED_USER_ID` | Message [@userinfobot](https://t.me/userinfobot) to get your numeric user ID |

### VK

You need **two tokens** because VK's API requires a user token for video uploads but accepts a community token for wall posts.

| Variable | Where to get it |
|---|---|
| `VK_COMMUNITY_TOKEN` | VK community settings → API tokens |
| `VK_USER_TOKEN` | Create a Standalone app at [vk.com/dev](https://vk.com/dev), authorize with `video,wall,offline` scopes |
| `VK_OWNER_ID` | Your community ID as a **negative number**, e.g. `-123456789` |

### Instagram

Requires a **Business or Creator** Instagram account connected to a Facebook Page.

| Variable | Where to get it |
|---|---|
| `INSTAGRAM_USER_ID` | Your Instagram account ID (available in Meta Graph API Explorer) |
| `INSTAGRAM_ACCESS_TOKEN` | A long-lived Page access token with `instagram_basic` and `instagram_content_publish` permissions, from [developers.facebook.com](https://developers.facebook.com) |

> **Token expiry:** Instagram long-lived access tokens expire after **60 days**. You will need to refresh the token periodically.

---

## Project structure

```
repost-bot/
├── bot.py            # Telegram bot — entry point
├── fetcher.py        # Downloads content from forwarded messages
├── transformer.py    # Applies mention substitutions from mentions.json
├── vk_poster.py      # Posts to VK community wall
├── ig_poster.py      # Posts to Instagram via Graph API
├── mentions.json     # Per-platform text substitution rules
├── config.py         # Loads environment variables
├── .env              # Your secrets (never commit this)
├── .env.example      # Template for .env
└── requirements.txt
```
