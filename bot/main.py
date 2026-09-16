import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.config import TELEGRAM_BOT_TOKEN
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
    app.run_polling()


if __name__ == "__main__":
    main()
