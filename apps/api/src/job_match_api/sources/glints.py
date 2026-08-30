from datetime import UTC, datetime

import httpx
from pydantic import BaseModel

from job_match_api.config import settings

PENARIK = "glints"

# cuplikan pendek untuk embedding — deskripsi utuh masuk isi_lengkap supaya
# tidak terpotong di 256 token dan menyisakan vektor yang hanya mewakili pembuka
MAKS_SNIPPET = 300


class GlintsError(Exception):
    """Kesalahan yang muncul saat memproses data dari scraper."""


class GlintsJob(BaseModel):
    id: str
    title: str
    company: str | None = None
    location: str | None = None
    salary: str | None = None
    link: str
    snippet: str | None = None
    isi_lengkap: str | None = None
    isi_lengkap_at: datetime | None = None
    updated: datetime | None = None
    type: str | None = None
    source: str = PENARIK


def _headers() -> dict[str, str]:
    return {"X-API-KEY": settings.scraper_api_key}


def _dari_item(item: dict) -> GlintsJob:
    isi = (item.get("description") or "").strip()
    return GlintsJob(
        id=item["id"],
        title=item["title"],
        company=item.get("company"),
        location=item.get("location"),
        salary=item.get("salary"),
        link=item["url"],
        snippet=isi[:MAKS_SNIPPET] or None,
        isi_lengkap=isi or None,
        isi_lengkap_at=datetime.now(UTC) if isi else None,
        updated=item.get("postedAt"),
    )


def daftar_keyword(kata: str) -> None:
    """Daftarkan kata kunci ke scraper. Upsert di sana, jadi aman dipanggil berulang."""
    url = f"{settings.scraper_url}/api/v1/jobs/keywords"
    try:
        respons = httpx.post(url, json={"keyword": kata}, headers=_headers(), timeout=15)
        respons.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise GlintsError(f"Scraper menolak keyword (HTTP {e.response.status_code})") from e
    except httpx.RequestError as e:
        raise GlintsError(f"Tidak bisa menghubungi scraper: {type(e).__name__}") from e


def search(days: int = 7, limit: int = 100) -> list[GlintsJob]:
    """Tarik lowongan yang sudah matang dari scraper. Tanpa filter keyword: satu
    lowongan hanya tercatat di bawah keyword yang menemukannya lebih dulu."""
    url = f"{settings.scraper_url}/api/v1/jobs"
    try:
        respons = httpx.get(
            url, params={"days": days, "limit": limit}, headers=_headers(), timeout=30
        )
        respons.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise GlintsError(f"Scraper menolak permintaan (HTTP {e.response.status_code})") from e
    except httpx.RequestError as e:
        raise GlintsError(f"Tidak bisa menghubungi scraper: {type(e).__name__}") from e

    return [_dari_item(item) for item in respons.json().get("jobs", [])]
