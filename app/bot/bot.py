from telegram.ext import (
    Application,
    CommandHandler,
)

from app.config.settings import settings
from app.bot.handlers import start, ping


class TelegramBot:

    def __init__(self):
        self.application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .build()
        )

        self.register_handlers()

    def register_handlers(self):
        self.application.add_handler(
            CommandHandler("start", start)
        )

        self.application.add_handler(
            CommandHandler("ping", ping)
        )

    def run(self):
        self.application.run_polling()