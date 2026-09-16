import hashlib
import os

from dotenv import load_dotenv

load_dotenv()


def _split_ids(raw: str) -> set[int]:
    return {int(part.strip()) for part in raw.split(",") if part.strip()}


def _split_usernames(raw: str) -> set[str]:
    return {part.strip().lstrip("@").lower() for part in raw.split(",") if part.strip()}


TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ALLOWED_TELEGRAM_IDS = _split_ids(os.environ.get("ALLOWED_TELEGRAM_IDS", ""))
ALLOWED_TELEGRAM_USERNAMES = _split_usernames(os.environ.get("ALLOWED_TELEGRAM_USERNAMES", ""))

# На Render бесплатный тариф поддерживает только Web Service (не Background Worker),
# поэтому там бот работает через webhook, а не long polling. Render сам задаёт PORT
# и RENDER_EXTERNAL_URL для веб-сервисов; локально их нет, и бот просто long-polling'ит.
PORT = int(os.environ.get("PORT", "10000"))
WEBHOOK_BASE_URL = os.environ.get("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = hashlib.sha256(f"path:{TELEGRAM_BOT_TOKEN}".encode()).hexdigest()
WEBHOOK_SECRET = hashlib.sha256(f"secret:{TELEGRAM_BOT_TOKEN}".encode()).hexdigest()
