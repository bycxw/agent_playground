"""Configuration for Invest Assistant."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Project paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    ZVT_DATA_DIR: Path = DATA_DIR / "zvt"
    MY_DATA_DIR: Path = DATA_DIR / "my"

    # Data provider
    DEFAULT_PROVIDER: str = "eastmoney"

    # Monitor settings
    MONITOR_CHECK_INTERVAL_MINUTES: int = 60  # 检查间隔
    MONITOR_DEFAULT_MARKET: str = "A股"  # A股/港股/ALL

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

    # Database
    DATABASE_URL: str = f"sqlite:///{MY_DATA_DIR}/invest_assistant.db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.ZVT_DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.MY_DATA_DIR.mkdir(parents=True, exist_ok=True)