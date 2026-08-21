import re
from collections.abc import Iterable

from job_match_api.cv.profil import ProfilCv
from job_match_api.db.models import Lowongan

TINGKAT_PROFIL = {"junior": 1, "menengah": 2, "senior": 3}

TINGKAT_JUDUL = {
    "intern": 0,
    "internship": 0,
    "magang": 0,
    "trainee": 0,
    "fresh graduate": 0,
    "junior": 1,
    "jr": 1,
    "entry level": 1,
    "senior": 3,
    "sr": 3,
    "lead": 3,
    "leader": 3,
    "principal": 3,
    "head": 3,
    "manager": 3,
    "supervisor": 3,
    "director": 5,
    "chief": 5,
    "vp": 5,
    "president": 5,
}

JARAK_LEVEL_MAKS = 2


def _tingkat_judul(judul: str) -> int | None:
    """Baca level dari judul lowongan. None kalau judulnya tidak menyebut level."""
    j = judul.lower()
    cocok = [t for kata, t in TINGKAT_JUDUL.items() if re.search(rf"\b{re.escape(kata)}\b", j)]
    # "Senior Engineering Manager" diambil tingkat tertingginya
    return max(cocok) if cocok else None


def _alasan_buang(
    low: Lowongan,
    tingkat_user: int,
    sudah_dikirim: frozenset[int],
) -> str | None:
    if low.id in sudah_dikirim:
        return "sudah pernah dikirim"

    tingkat = _tingkat_judul(low.title)
    if tingkat is not None and abs(tingkat - tingkat_user) >= JARAK_LEVEL_MAKS:
        return f"level judul terlalu jauh ({tingkat} vs {tingkat_user})"

    return None


def saring_kasar(
    profil: ProfilCv,
    lowongan: Iterable[Lowongan],
    sudah_dikirim: frozenset[int] = frozenset(),
) -> list[Lowongan]:
    """Buang lowongan yang jelas tidak mungkin, tanpa LLM. Yang menilai tetap OTAK.

    Kecocokan bidang tidak diperiksa di sini: itu tugas jarak vektor di
    ambil_lowongan_belum_dinilai. Diukur 2026-08-19, aturan kata lama meloloskan
    10 dari 263 dan 9 di antaranya justru peringkat 50-218 dari kedekatan ke CV.
    """
    tingkat_user = TINGKAT_PROFIL.get(profil.level.lower(), 2)
    return [low for low in lowongan if _alasan_buang(low, tingkat_user, sudah_dikirim) is None]
