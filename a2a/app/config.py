from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    RAZORPAY_KEY_ID: str = "rzp_test_XXXXXXXXXXXXXXXX"
    RAZORPAY_KEY_SECRET: str = "YOUR_SECRET_HERE"
    RAZORPAY_WEBHOOK_SECRET: str = "WEBHOOK_SECRET_HERE"
    APP_ENV: str = "development"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "*"]
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/razorai"
    OPENAI_API_KEY: str = ""


settings = Settings()
