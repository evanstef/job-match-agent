import json
from datetime import datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

from job_match_api.config import settings


class JoobleError(Exception):
    """Kesalahan yang muncul saat memproses data Jooble."""


class JoobleJob(BaseModel):
    id: int
    title: str
    company: str | None = None
    location: str | None = None
    snippet: str | None = None
    salary: str | None = None
    type: str | None = None
    source: str | None = None
    link: str
    updated: datetime | None = None


def _dari_json(data: dict) -> list[JoobleJob]:
    """Ubah body respons Jooble (dari file atau dari API) jadi daftar JoobleJob."""
    return [JoobleJob(**job) for job in data.get("jobs", [])]


def baca_dari_file(file_path: Path) -> list[JoobleJob]:
    data = json.loads(Path(file_path).read_text(encoding="utf-8"))
    return _dari_json(data)


# di atas 100, Jooble diam-diam mengirim 30 — bukan error, bukan peringatan
MAKS_PER_HALAMAN = 100


def search(
    keywords: str,
    location: str,
    result_on_page: int = MAKS_PER_HALAMAN,
    halaman: int = 1,
) -> list[JoobleJob]:
    # di cek dulu ada gak env api jooble nya
    if not settings.jooble_api_key:
        raise JoobleError("API key Jooble tidak ditemukan")

    url = f"{settings.jooble_base_url}/{settings.jooble_api_key}"
    body = {
        "keywords": keywords,
        "location": location,
        "ResultOnPage": str(min(result_on_page, MAKS_PER_HALAMAN)),
        "page": str(halaman),
    }

    try:
        respons = httpx.post(url, json=body, timeout=30)
        respons.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise JoobleError(f"Jooble menolak permintaan (HTTP {e.response.status_code})") from e
    except httpx.RequestError as e:
        raise JoobleError(f"Tidak bisa menghubungi Jooble: {type(e).__name__}") from e

    return _dari_json(respons.json())
