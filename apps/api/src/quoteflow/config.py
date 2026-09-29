from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mode: str = "DEMO"
    database_url: str = "sqlite:///./quoteflow.db"
    public_base_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"
    session_secure: bool = False
    session_ttl_hours: int = 12
    portal_ttl_days: int = 14
    approval_discount_threshold: str = "10.00"
    default_tax_percent: str = "0.00"
    default_contingency_percent: str = "0.00"
    openai_model: str = ""
    openai_api_key: str = ""
    hubspot_access_token: str = ""
    hubspot_enabled: bool = False
    hubspot_max_attempts: int = 3
    worker_backoff_seconds: int = 30
    worker_poll_seconds: int = 10
    max_upload_bytes: int = 5_000_000
    asset_dir: str = "./assets"
    demo_seed: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
