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
    "lead": 4,
    "principal": 4,
    "head of": 4,
    "manager": 4,
    "director": 4,
    "chief": 4,
    "vp": 4,
}

JARAK_LEVEL_MAKS = 2


def _tingkat_judul(judul: str) -> int | None:
    """Baca level dari judul lowongan. None kalau judulnya tidak menyebut level."""
    j = judul.lower()
    cocok = [t for kata, t in TINGKAT_JUDUL.items() if re.search(rf"\b{re.escape(kata)}\b", j)]
    # "Senior Engineering Manager" dibaca sebagai manager, bukan senior
    return max(cocok) if cocok else None


def _pola_bidang(profil: ProfilCv) -> re.Pattern[str]:
    """Susun satu pola dari posisi + skill user untuk menandai lowongan sebidang."""
    teks = " ".join([profil.posisi, *profil.skill]).lower()
    kata = {k for k in re.findall(r"[a-z]+", teks) if len(k) > 2}
    return re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(kata)) + r")\b")


def _alasan_buang(
    low: Lowongan,
    tingkat_user: int,
    pola: re.Pattern[str],
    sudah_dikirim: frozenset[int],
) -> str | None:
    if low.id in sudah_dikirim:
        return "sudah pernah dikirim"

    tingkat = _tingkat_judul(low.title)
    if tingkat is not None and abs(tingkat - tingkat_user) >= JARAK_LEVEL_MAKS:
        return f"level judul terlalu jauh ({tingkat} vs {tingkat_user})"

    if not pola.search(f"{low.title} {low.snippet or ''}".lower()):
        return "tidak ada jejak bidang di judul/snippet"

    return None


def saring_kasar(
    profil: ProfilCv,
    lowongan: Iterable[Lowongan],
    sudah_dikirim: frozenset[int] = frozenset(),
) -> list[Lowongan]:
    """Buang lowongan yang jelas tidak mungkin, tanpa LLM. Yang menilai tetap OTAK."""
    tingkat_user = TINGKAT_PROFIL.get(profil.level.lower(), 2)
    pola = _pola_bidang(profil)
    return [
        low for low in lowongan if _alasan_buang(low, tingkat_user, pola, sudah_dikirim) is None
    ]
