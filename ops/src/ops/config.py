"""Configuration for ops service."""
from pathlib import Path
from typing import Optional

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Paths and DATABASE_URL are derived from MY_DATA_DIR so overriding the
    storage root via env (e.g. MY_DATA_DIR=/tmp/foo) follows through to
    the SQLite location.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Project paths — data_storage/ is gitignored, sibling to common/, data/.
    # Data layer config (BAOSTOCK_DATA_DIR, DB_PATH) lives in data.config.
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = BASE_DIR / "data_storage"
    MY_DATA_DIR: Path = DATA_DIR / "my"

    # Monitor settings
    MONITOR_CHECK_INTERVAL_MINUTES: int = 60
    MONITOR_DEFAULT_MARKET: str = "A股"   # A股 / 港股 / ALL

    # Notification
    NOTIFICATION_EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFICATION_EMAIL_TO: str = ""

    NOTIFICATION_TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Override to point ops state DB elsewhere; default tracks MY_DATA_DIR.
    DATABASE_URL_OVERRIDE: Optional[str] = None

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return f"sqlite:///{self.MY_DATA_DIR}/ops.db"


settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.MY_DATA_DIR.mkdir(parents=True, exist_ok=True)
