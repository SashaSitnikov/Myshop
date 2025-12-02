import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list[int] = None

    # CryptoBot
    CRYPTOBOT_TOKEN: str = os.getenv("CRYPTOBOT_TOKEN", "")
    CRYPTOBOT_IS_TESTNET: bool = os.getenv("CRYPTOBOT_TESTNET", "false").lower() == "true"

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot/database/bot.db")

    # Telethon (публичные значения)
    API_ID: int = 2040
    API_HASH: str = "b18441a1ff607e10a989891a5462e627"

    # Sessions folder
    SESSIONS_DIR: str = "bot/sessions"

    def __post_init__(self):
        admin_ids = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS = [int(x.strip()) for x in admin_ids.split(",") if x.strip()]


config = Config()
