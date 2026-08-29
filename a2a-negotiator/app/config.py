from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Application Configuration & Environment Variables.
    Strictly validates system settings, default guardrails, and API keys.
    """

    # --- Application Metadata ---
    APP_NAME: str = "Razorpay A2A Dynamic Negotiator Engine"
    ENV: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Toggle debug logging mode")

    # --- Razorpay Credentials ---
    RAZORPAY_KEY_ID: str = Field(..., description="Razorpay API Key ID (rzp_test_... or rzp_live_...)")
    RAZORPAY_KEY_SECRET: str = Field(..., description="Razorpay API Key Secret")
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = Field(
        default=None, description="Secret used to verify Razorpay webhook signatures"
    )

    # --- Database & Cache ---
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/a2a_negotiator",
        description="Async PostgreSQL Connection String",
    )
    REDIS_URL: Optional[str] = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for negotiation session locking",
    )

    # --- Global Default Financial Guardrails ---
    GLOBAL_MIN_MARGIN_PCT: float = Field(
        default=0.15,
        ge=0.0,
        le=0.80,
        description="Absolute minimum profit margin allowed across all products (e.g., 0.15 = 15%)",
    )
    GLOBAL_MAX_DISCOUNT_PCT: float = Field(
        default=0.25,
        ge=0.0,
        le=0.50,
        description="Maximum single-transaction discount cap (e.g., 0.25 = 25%)",
    )
    MAX_NEGOTIATION_ROUNDS: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum counter-offer iterations before automated final reject/accept",
    )

    # --- LLM Provider Settings (LangChain / LangGraph Engine) ---
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key for agent intelligence")
    MODEL_NAME: str = Field(default="gpt-4o-mini", description="LLM model powering negotiator agent decisioning")

    # --- Config Pydantic Behavior ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings singleton instance
settings = Settings()