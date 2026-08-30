from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env tinggal di apps/api. Dipatok dari lokasi berkas ini, bukan dari folder
# proses — supaya nilai yang kebaca tidak berubah tergantung dipanggil dari mana
BERKAS_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Semua konfigurasi dibaca dari environment / file .env."""

    model_config = SettingsConfigDict(
        env_file=BERKAS_ENV,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"

    database_url: str

    jooble_api_key: str = ""
    jooble_base_url: str = "https://id.jooble.org/api"
    scraper_url: str = "http://localhost:3000"
    scraper_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    model_cache_dir: str = ".model-cache"
    telegram_bot_token: str = ""
    whatsapp_url: str = "http://localhost:3456"
    whatsapp_tujuan: str = ""
    whatsapp_api_key: str = ""

    # mati secara default supaya menjalankan API di laptop tidak ikut mengirim pesan
    penjadwal_aktif: bool = False

    # asal frontend yang boleh membawa cookie. Dipisah koma kalau lebih dari satu.
    # WAJIB alamat spesifik — "*" ditolak browser kalau request-nya membawa kredensial
    frontend_url: str = "http://localhost:3010"

    @property
    def daftar_frontend(self) -> list[str]:
        return [a.strip() for a in self.frontend_url.split(",") if a.strip()]

    jwt_secret: str
    jwt_algorithm: str = "HS256"


settings = Settings()
