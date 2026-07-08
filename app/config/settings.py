from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    base_url: str
    telegram_bot_token: str


settings = Settings(
    base_url=os.environ["BASE_URL"],
    telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
)