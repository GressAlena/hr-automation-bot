from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from bot import db
from bot.auth import restricted

_STATUS_LABELS = {
    "new": "новый",
    "invited": "приглашён",
    "on_hold": "отложен",
    "rejected": "отказ",
}


def format_candidate(candidate: dict) -> str:
    status_label = _STATUS_LABELS.get(candidate["status"], candidate["status"])
    return (
        f"Кандидат: {candidate['file_name']}\n"
        f"Балл: {candidate['score']}/100\n"
        f"Статус: {status_label}\n\n"
        f"Итог: {candidate['summary']}\n\n"
        f"Сильные стороны:\n{candidate['strengths']}\n\n"
        f"Пробелы:\n{candidate['gaps']}\n\n"
        f"Рекомендация: {candidate['recommendation']}"
    )


def status_keyboard(candidate_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Пригласить", callback_data=f"status:{candidate_id}:invited"),
                InlineKeyboardButton("🕐 Отложить", callback_data=f"status:{candidate_id}:on_hold"),
                InlineKeyboardButton("❌ Отказать", callback_data=f"status:{candidate_id}:rejected"),
            ]
        ]
    )


@restricted
async def status_update_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, candidate_id, status = query.data.split(":", 2)
    db.update_candidate_status(candidate_id, status)
    await query.answer("Статус обновлён")
    candidate = db.get_candidate(candidate_id)
    await query.edit_message_text(
        format_candidate(candidate),
        reply_markup=status_keyboard(candidate_id),
    )


status_update_handler = CallbackQueryHandler(status_update_callback, pattern=r"^status:")
