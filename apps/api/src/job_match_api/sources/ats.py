import html
import re

import httpx

# tanpa User-Agent, Workable membalas 403
USER_AGENT = "job-match-agent/0.1 (bot pencari lowongan pribadi)"

TIMEOUT = 20
MIN_TEKS = 200


class AtsError(Exception):
    """Isi lowongan tidak bisa diambil dari ATS."""


def _bersihkan(teks: str) -> str:
    polos = html.unescape(teks or "")
    tanpa_tag = re.sub(r"</?[a-zA-Z][^<>]*>", " ", polos)
    return re.sub(r"\s+", " ", tanpa_tag).strip()


def _slug_kandidat(perusahaan: str) -> list[str]:
    """Nama perusahaan jarang sama persis dengan slug board-nya, jadi dicoba beberapa bentuk."""
    n = re.sub(r"^(PT|CV)\.?\s+", "", perusahaan, flags=re.IGNORECASE)
    n = re.sub(
        r"\s*(Pte\.?\s*Ltd\.?|Ltd\.?|Inc\.?|Group|Indonesia)$", "", n, flags=re.IGNORECASE
    ).strip()

    rapat = re.sub(r"[^a-z0-9]", "", n.lower())
    strip = re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
    return [s for s in dict.fromkeys([rapat, strip]) if s]


def _ambil(url: str) -> dict | None:
    try:
        respons = httpx.get(
            url,
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        respons.raise_for_status()
        return respons.json()
    except (httpx.HTTPError, ValueError):
        return None


def _greenhouse(slug: str, judul: set[str]) -> dict[str, str]:
    data = _ambil(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    if not data or not data.get("jobs"):
        return {}
    return {
        j["title"]: _bersihkan(j.get("content", "")) for j in data["jobs"] if j["title"] in judul
    }


def _workable(slug: str, judul: set[str]) -> dict[str, str]:
    data = _ambil(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    if not data or not data.get("jobs"):
        return {}
    return {
        j["title"]: _bersihkan(f"{j.get('description', '')} {j.get('requirements', '')}")
        for j in data["jobs"]
        if j["title"] in judul
    }


def _smartrecruiters(slug: str, judul: set[str]) -> dict[str, str]:
    daftar = _ambil(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings")
    # slug salah tetap dibalas 200 dengan daftar kosong, jadi totalFound yang jadi patokan
    if not daftar or not daftar.get("totalFound"):
        return {}

    hasil = {}
    for p in daftar.get("content", []):
        if p["name"] not in judul:
            continue
        # isi lengkapnya cuma ada di detail, jadi diambil hanya untuk yang dicari
        detail = _ambil(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{p['id']}")
        bagian = (detail or {}).get("jobAd", {}).get("sections", {})
        teks = " ".join(
            _bersihkan(b.get("text", "")) for b in bagian.values() if isinstance(b, dict)
        )
        if len(teks) >= MIN_TEKS:
            hasil[p["name"]] = teks
    return hasil


PENGAMBIL = {
    "boards.greenhouse.io": _greenhouse,
    "smartrecruiters.com": _smartrecruiters,
    "workable.com": _workable,
}


def didukung(source: str | None) -> bool:
    return source in PENGAMBIL


def ambil_board(source: str, perusahaan: str, judul: set[str]) -> dict[str, str]:
    """Ambil isi lengkap beberapa lowongan sekaligus dari satu board. Kosong kalau tidak ketemu."""
    pengambil = PENGAMBIL.get(source)
    if pengambil is None:
        raise AtsError(f"Sumber '{source}' belum didukung")

    for slug in _slug_kandidat(perusahaan):
        hasil = pengambil(slug, judul)
        if hasil:
            return {j: t for j, t in hasil.items() if len(t) >= MIN_TEKS}
    return {}
