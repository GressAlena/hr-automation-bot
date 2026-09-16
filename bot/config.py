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
