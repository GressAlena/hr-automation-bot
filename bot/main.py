import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.config import (
    PORT,
    TELEGRAM_BOT_TOKEN,
    WEBHOOK_BASE_URL,
    WEBHOOK_PATH,
    WEBHOOK_SECRET,
)
from bot.handlers import candidates, common

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def build_application() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", common.start))
    app.add_handler(CommandHandler("help", common.start))
    app.add_handler(CommandHandler("reset", common.reset))

    app.add_handler(candidates.status_update_handler)

    app.add_handler(MessageHandler(filters.Document.ALL, common.handle_document))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, common.handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, common.handle_text))

    return app


def main() -> None:
    app = build_application()

    if WEBHOOK_BASE_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH,
            webhook_url=f"{WEBHOOK_BASE_URL}/{WEBHOOK_PATH}",
            secret_token=WEBHOOK_SECRET,
        )
    else:
        app.run_polling()


if __name__ == "__main__":
    main()
