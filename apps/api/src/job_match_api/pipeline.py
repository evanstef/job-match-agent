import logging
import time

from pydantic import BaseModel
from sqlalchemy.orm import Session

from job_match_api.brain.otak import Hasil, OtakError, Preferensi, nilai
from job_match_api.brain.saring import saring_kasar
from job_match_api.cv.profil import ProfilCv
from job_match_api.db.models import Cv, Lowongan, User
from job_match_api.db.repository import (
    ambil_cv_terbaru,
    ambil_lowongan_belum_dinilai,
    catat_penilaian,
    simpan_vektor_cv,
)
from job_match_api.vektor import VektorError, dari_profil

logger = logging.getLogger(__name__)

PREFERENSI_DEFAULT = Preferensi(lokasi=["Jakarta", "Tangerang"], mau_remote=True)

# Lantai, bukan tebing. Satu lowongan yang sama dinilai 5x menghasilkan 45/45/45/70/70
# (17 Agu) dan 36/76/36/56/56 (19 Agu) — ambang di dalam pita itu jadi undian.
# Yang menyeleksi urutan skor + MAKS_KIRIM; lantai cuma menahan waktu tak ada yang bagus.
AMBANG_SKOR = 35
MAKS_KIRIM = 10
JEDA_DETIK = 10


class PipelineError(Exception):
    """Perakit tidak bisa jalan."""


class LowonganTerpilih(BaseModel):
    id: int
    title: str
    company: str | None
    link: str
    skor: int
    vonis: str
    ringkasan: str
    detail_terbaca: bool


class HasilJalan(BaseModel):
    kandidat: int
    dinilai: int
    gagal: int
    terpilih: list[LowonganTerpilih]


def _preferensi(user: User) -> Preferensi:
    if user.preferensi is None:
        return PREFERENSI_DEFAULT

    return Preferensi(
        lokasi=user.preferensi.lokasi,
        bersedia_relokasi=user.preferensi.bersedia_relokasi,
        mau_remote=user.preferensi.mau_remote,
    )


def _vektor_cv(db: Session, cv: Cv) -> list[float] | None:
    """Vektor CV untuk mengurutkan lowongan. Kesempatan kedua kalau belum ada.

    Yang mengisinya sungguhan adalah jalur upload. Ini jaring di bawahnya: tanpa
    ini, embedding yang gagal sekali waktu upload berarti user itu memakai urutan
    cadangan selamanya, tanpa satu pun error muncul. Hasilnya disimpan supaya
    kolom yang kosong itu benar-benar sembuh, bukan dihitung ulang tiap putaran.
    """
    if cv.embedding is not None:
        return [float(x) for x in cv.embedding]

    try:
        vektor = dari_profil(cv.profil)
    except VektorError as e:
        logger.warning("Vektor CV %s gagal dihitung: %s", cv.id, e)
        return None

    simpan_vektor_cv(db, cv, vektor)
    return vektor


def _terpilih(low: Lowongan, hasil: Hasil) -> LowonganTerpilih:
    return LowonganTerpilih(
        id=low.id,
        title=low.title,
        company=low.company,
        link=low.link,
        skor=hasil.skor,
        vonis=hasil.vonis,
        ringkasan=hasil.ringkasan,
        detail_terbaca=hasil.detail_terbaca,
    )


def jalankan(db: Session, user_id: int, maks_dinilai: int = 10) -> HasilJalan:
    # ambil cv yang terbaru dulu
    cv = ambil_cv_terbaru(db, user_id)
    if cv is None or cv.profil is None:
        raise PipelineError("CV tidak ditemukan atau belum selesai diproses")

    profil = ProfilCv(**cv.profil)
    pref = _preferensi(cv.user)

    # tanpa vektor, kandidat jatuh ke urutan id dan batas jarak tidak berlaku —
    # kuota Groq habis untuk lowongan asal-asalan. Lebih baik putaran ini gagal.
    vektor = _vektor_cv(db, cv)
    if vektor is None:
        raise PipelineError("Vektor CV belum ada — kandidat tidak bisa diurutkan")

    lowongan = ambil_lowongan_belum_dinilai(db, user_id, vektor)
    kandidat = saring_kasar(profil, lowongan)

    # dinilai satu per satu, dijeda karena kuota Groq dihitung per menit
    dinilai: list[tuple[Lowongan, Hasil]] = []
    gagal = 0
    for urutan, low in enumerate(kandidat[:maks_dinilai]):
        if urutan:
            time.sleep(JEDA_DETIK)
        try:
            dinilai.append((low, nilai(cv.teks_mentah, pref, low, low.isi_lengkap, profil.peran)))
        except OtakError as e:
            # satu lowongan gagal tidak boleh mematikan seluruh putaran
            gagal += 1
            logger.warning("Lowongan %s gagal dinilai: %s", low.id, e)

    # semua yang dinilai dicatat, bukan cuma yang dikirim — supaya tidak dinilai ulang besok
    catat_penilaian(db, user_id, [(low.id, h.vonis, h.skor) for low, h in dinilai])

    layak = [(low, h) for low, h in dinilai if h.vonis != "SKIP" and h.skor >= AMBANG_SKOR]
    layak.sort(key=lambda pasangan: pasangan[1].skor, reverse=True)

    return HasilJalan(
        kandidat=len(kandidat),
        dinilai=len(dinilai),
        gagal=gagal,
        terpilih=[_terpilih(low, h) for low, h in layak[:MAKS_KIRIM]],
    )
