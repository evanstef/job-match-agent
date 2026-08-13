import re
from collections.abc import Iterable
from typing import NamedTuple

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
PANJANG_KATA_MIN = 3
MIN_SKILL_COCOK = 2


def _tingkat_judul(judul: str) -> int | None:
    """Baca level dari judul lowongan. None kalau judulnya tidak menyebut level."""
    j = judul.lower()
    cocok = [t for kata, t in TINGKAT_JUDUL.items() if re.search(rf"\b{re.escape(kata)}\b", j)]
    # "Senior Engineering Manager" diambil tingkat tertingginya
    return max(cocok) if cocok else None


class PolaBidang(NamedTuple):
    peran: re.Pattern[str] | None
    skill: tuple[re.Pattern[str], ...]

    def cocok(self, teks: str) -> bool:
        # profil tidak menyisakan kata apa pun — aturan bidang dilewati, bukan meloloskan semua
        if self.peran is None and not self.skill:
            return True
        if self.peran is not None and self.peran.search(teks):
            return True

        # profil berskill 1 tidak akan pernah mencapai 2 — syaratnya diturunkan, bukan dibuat mustahil
        butuh = min(MIN_SKILL_COCOK, len(self.skill))
        return sum(bool(p.search(teks)) for p in self.skill) >= butuh


def _kata(teks: str) -> list[str]:
    return [k for k in re.findall(r"[a-z]+", teks.lower()) if len(k) >= PANJANG_KATA_MIN]


def _pola_bidang(profil: ProfilCv) -> PolaBidang:
    """Kata peran diambil dari kata terakhir posisi. "Front End Web Developer" -> "developer".

    Kata depannya ("front", "web") terlalu umum: bikin "Front Office Staff" ikut lolos.
    """
    kata_posisi = _kata(profil.posisi)
    peran = re.compile(rf"\b{re.escape(kata_posisi[-1])}\b") if kata_posisi else None
    skill = {k for s in profil.skill for k in _kata(s)}
    return PolaBidang(peran, tuple(re.compile(rf"\b{re.escape(k)}\b") for k in sorted(skill)))


def _alasan_buang(
    low: Lowongan,
    tingkat_user: int,
    pola: PolaBidang,
    sudah_dikirim: frozenset[int],
) -> str | None:
    if low.id in sudah_dikirim:
        return "sudah pernah dikirim"

    tingkat = _tingkat_judul(low.title)
    if tingkat is not None and abs(tingkat - tingkat_user) >= JARAK_LEVEL_MAKS:
        return f"level judul terlalu jauh ({tingkat} vs {tingkat_user})"

    if not pola.cocok(f"{low.title} {low.snippet or ''}".lower()):
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
