import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_ALLOWED_USER_ID = int(os.environ["TELEGRAM_ALLOWED_USER_ID"])

VK_COMMUNITY_TOKEN = os.environ["VK_COMMUNITY_TOKEN"]
VK_USER_TOKEN = os.environ["VK_USER_TOKEN"]
VK_OWNER_ID = int(os.environ["VK_OWNER_ID"])

INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]
INSTAGRAM_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]

