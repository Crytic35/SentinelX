import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SentinelX"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sentinelx.db")
    PAYPAL_CLIENT_ID: str = os.getenv("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET: str = os.getenv("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_MODE: str = os.getenv("PAYPAL_MODE", "sandbox")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "sentinelx_zero_trust_secret_key_demo_change_in_prod")
    SHADOW_MODE: bool = os.getenv("SHADOW_MODE", "false").lower() == "true"
    GLOBAL_FREEZE: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

