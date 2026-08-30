import html
import json
import logging
import re
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# tanpa User-Agent, Workable membalas 403
USER_AGENT = "job-match-agent/0.1 (bot pencari lowongan pribadi)"

TIMEOUT = 20
MIN_TEKS = 200
# SmartRecruiters membalas maksimal 100 posting per permintaan. Sebagian board sangat
# besar (Turner & Townsend 2.915), jadi dibatasi -- yang terpotong dicatat di log.
PER_HALAMAN = 100
MAKS_HALAMAN = 5


class AtsError(Exception):
    """Isi lowongan tidak bisa diambil dari ATS."""


def _bersihkan(teks: str) -> str:
    polos = html.unescape(teks or "")
    tanpa_tag = re.sub(r"</?[a-zA-Z][^<>]*>", " ", polos)
    return re.sub(r"\s+", " ", tanpa_tag).strip()


def _slug_kandidat(perusahaan: str) -> list[str]:
    """Nama perusahaan jarang sama persis dengan slug board-nya, jadi dicoba beberapa bentuk.

    Kata pertama saja sering justru yang benar: "AYANA Hospitality" -> ayana (129 lowongan),
    "Techconnect.id" -> techconnect. Diukur 2026-08-22: menambah varian ini menemukan 4 board
    lagi dari 23 perusahaan yang tadinya buntu.
    """
    n = re.sub(r"^(PT|CV)\.?\s+", "", perusahaan, flags=re.IGNORECASE)
    n = re.sub(
        r"\s*(Pte\.?\s*Ltd\.?|Ltd\.?|Inc\.?|Tbk\.?|Group|Indonesia)$", "", n, flags=re.IGNORECASE
    ).strip()
    # "Funding Societies | Modalku Group" -> board-nya "fundingsocieties" (potong di |),
    # tapi "Stockbit | Bibit" -> board-nya "stockbitbibit" (justru utuh). Dua-duanya dicoba.
    depan = n.split("|")[0].split("(")[0].strip()

    bentuk = []
    for teks in dict.fromkeys([n, depan]):
        kata = re.findall(r"[a-z0-9]+", teks.lower())
        if not kata:
            continue
        bentuk += ["".join(kata), "-".join(kata), "".join(kata[:2]), "-".join(kata[:2]), kata[0]]
    return [s for s in dict.fromkeys(bentuk) if len(s) > 2]


def _kunci_judul(judul: str) -> str:
    """Judul dari Jooble sering beda tipis dengan nama posting di board.

    Disamakan seperlunya saja -- huruf kecil, tanda baca dibuang, awalan "Copy of"
    dibuang. Sengaja TIDAK fuzzy: salah cocok berarti isi iklan perusahaan lain
    menempel ke lowongan ini tanpa suara.
    """
    t = re.sub(r"^\s*copy of\s+", "", judul or "", flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def _peta_judul(judul: set[str]) -> dict[str, str]:
    return {_kunci_judul(j): j for j in judul}


def _ambil(url: str) -> dict | list | None:
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


def _ld_jobposting(url: str) -> str:
    """Ambil deskripsi dari data terstruktur schema.org di halaman lowongan.

    Diterbitkan situsnya sendiri supaya terbaca Google Jobs, jadi bentuknya stabil --
    jauh lebih kokoh daripada menebak susunan HTML-nya.
    """
    try:
        respons = httpx.get(
            url, timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        )
        respons.raise_for_status()
    except httpx.HTTPError:
        return ""

    for blok in re.findall(
        r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', respons.text, re.DOTALL
    ):
        try:
            data = json.loads(blok)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == "JobPosting":
            return _bersihkan(data.get("description", ""))
    return ""


def _breezy(slug: str, judul: set[str]) -> dict[str, str]:
    """Daftar breezy tidak memuat deskripsi, jadi halaman tiap lowongan dibuka -- tapi
    hanya untuk judul yang memang dicari."""
    daftar = _ambil(f"https://{slug}.breezy.hr/json")
    if not isinstance(daftar, list):
        return {}

    peta = _peta_judul(judul)
    hasil = {}
    for j in daftar:
        kunci = _kunci_judul(j.get("name", ""))
        if kunci not in peta or not j.get("url"):
            continue
        teks = _ld_jobposting(j["url"])
        if len(teks) >= MIN_TEKS:
            hasil[peta[kunci]] = teks
    return hasil


def _greenhouse(slug: str, judul: set[str]) -> dict[str, str]:
    data = _ambil(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    if not data or not data.get("jobs"):
        return {}
    peta = _peta_judul(judul)
    return {
        peta[k]: _bersihkan(j.get("content", ""))
        for j in data["jobs"]
        if (k := _kunci_judul(j["title"])) in peta
    }


def _workable(slug: str, judul: set[str]) -> dict[str, str]:
    data = _ambil(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    if not data or not data.get("jobs"):
        return {}
    peta = _peta_judul(judul)
    return {
        peta[k]: _bersihkan(f"{j.get('description', '')} {j.get('requirements', '')}")
        for j in data["jobs"]
        if (k := _kunci_judul(j["title"])) in peta
    }


def _smartrecruiters(slug: str, judul: set[str]) -> dict[str, str]:
    dasar = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    daftar = _ambil(f"{dasar}?limit={PER_HALAMAN}")
    # slug salah tetap dibalas 200 dengan daftar kosong, jadi totalFound yang jadi patokan
    if not daftar or not daftar.get("totalFound"):
        return {}

    total = daftar["totalFound"]
    posting = list(daftar.get("content", []))
    for halaman in range(1, MAKS_HALAMAN):
        if len(posting) >= total:
            break
        lanjut = _ambil(f"{dasar}?limit={PER_HALAMAN}&offset={halaman * PER_HALAMAN}")
        if not lanjut or not lanjut.get("content"):
            break
        posting.extend(lanjut["content"])

    if len(posting) < total:
        logger.warning(
            "Board %s: %s dari %s posting diperiksa, sisanya dilewati (rem MAKS_HALAMAN)",
            slug,
            len(posting),
            total,
        )

    peta = _peta_judul(judul)
    hasil = {}
    for p in posting:
        kunci = _kunci_judul(p["name"])
        if kunci not in peta:
            continue
        # isi lengkapnya cuma ada di detail, jadi diambil hanya untuk yang dicari
        detail = _ambil(f"{dasar}/{p['id']}")
        bagian = (detail or {}).get("jobAd", {}).get("sections", {})
        teks = " ".join(
            _bersihkan(b.get("text", "")) for b in bagian.values() if isinstance(b, dict)
        )
        if len(teks) >= MIN_TEKS:
            hasil[peta[kunci]] = teks
    return hasil


def _manatal(slug: str, judul: set[str]) -> dict[str, str]:
    """Board Manatal bisa sangat besar (MatchaTalent 3.090), jadi dicari per judul.

    Menelusuri halaman butuh 31 permintaan untuk satu perusahaan; `search` menyempitkan
    ke puluhan, dan yang ditembak cuma judul yang memang dicari.
    """
    dasar = f"https://api.manatal.com/open/v3/career-page/{slug}/jobs/"
    peta = _peta_judul(judul)

    hasil = {}
    for kunci, asli in peta.items():
        data = _ambil(f"{dasar}?page_size={PER_HALAMAN}&search={quote(asli)}")
        for j in (data or {}).get("results", []):
            if _kunci_judul(j.get("position_name", "")) != kunci:
                continue
            teks = _bersihkan(j.get("description", ""))
            if len(teks) >= MIN_TEKS:
                hasil[asli] = teks
            break
    return hasil


def _teamtailor(slug: str, judul: set[str]) -> dict[str, str]:
    """Teamtailor menerbitkan JSON Feed di /jobs.json — isi penuh ada di content_html."""
    data = _ambil(f"https://{slug}.teamtailor.com/jobs.json")
    peta = _peta_judul(judul)
    return {
        peta[k]: teks
        for j in (data or {}).get("items", [])
        if (k := _kunci_judul(j.get("title", ""))) in peta
        and len(teks := _bersihkan(j.get("content_html", ""))) >= MIN_TEKS
    }


def _jobsoid(slug: str, judul: set[str]) -> dict[str, str]:
    data = _ambil(f"https://{slug}.jobsoid.com/api/v1/jobs")
    peta = _peta_judul(judul)
    return {
        peta[k]: teks
        for j in (data or [])
        if isinstance(j, dict)
        and (k := _kunci_judul(j.get("title", ""))) in peta
        and len(teks := _bersihkan(j.get("description", ""))) >= MIN_TEKS
    }


PENGAMBIL = {
    "boards.greenhouse.io": _greenhouse,
    "breezy.hr": _breezy,
    "jobsoid.com": _jobsoid,
    "teamtailor.com": _teamtailor,
    "manatal.com": _manatal,
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
