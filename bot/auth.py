import functools

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import ALLOWED_TELEGRAM_IDS, ALLOWED_TELEGRAM_USERNAMES


def _is_allowed(user) -> bool:
    if user is None:
        return False
    if user.id in ALLOWED_TELEGRAM_IDS:
        return True
    return bool(user.username) and user.username.lower() in ALLOWED_TELEGRAM_USERNAMES


def restricted(handler):
    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not _is_allowed(user):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "У вас нет доступа к этому боту. Обратитесь к администратору HR-бота."
                )
            return None
        return await handler(update, context, *args, **kwargs)

    return wrapper
