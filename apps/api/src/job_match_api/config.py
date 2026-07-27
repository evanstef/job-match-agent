from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Semua konfigurasi dibaca dari environment / file .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"

    database_url: str = "postgresql+psycopg://jobmatch:jobmatch@localhost:5433/jobmatch"

    jooble_api_key: str = ""
    jooble_base_url: str = "https://id.jooble.org/api"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    telegram_bot_token: str = ""

    jwt_secret: str = "ganti-di-production"
    jwt_algorithm: str = "HS256"


settings = Settings()
