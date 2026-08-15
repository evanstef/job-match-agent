import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session

from job_match_api.db.models import User
from job_match_api.db.repository import ambil_user_siap, simpan_lowongan
from job_match_api.sources.jooble import JoobleError, search

logger = logging.getLogger(__name__)

# Kata kunci BOLEH digabung dipisah koma — terbukti satu permintaan mengembalikan
# campuran beberapa bidang sekaligus.
#
# Lokasi TIDAK BOLEH. Diuji dengan "Jakarta, Tangerang, Surabaya": dari 300 lowongan
# tidak ada satu pun Surabaya, padahal "Surabaya" sendirian mengembalikan 220. Jooble
# menjatuhkannya tanpa error. Jadi lokasi ditarik satu per satu.
PEMISAH = ", "

MAKS_KATA_KUNCI = 5
MAKS_LOKASI = 3

# rem kuota: kota x halaman tidak boleh melebihi ini dalam satu putaran.
# 3 permintaan x 3 putaran x 30 hari = 270/bulan, dari batas Jooble 500.
MAKS_PERMINTAAN = 3

LOKASI_DEFAULT = "Indonesia"


class HasilTarik(BaseModel):
    kata_kunci: str
    lokasi: list[str]
    halaman: int
    permintaan: int
    dibaca: int
    baru: int


def _kata_kunci(user: User) -> list[str]:
    """Dari preferensi kalau diisi, kalau tidak dari posisi hasil baca CV."""
    pref = user.preferensi
    if pref and pref.keywords:
        return pref.keywords

    cv = max(
        (c for c in user.cvs if c.profil),
        key=lambda c: c.id,
        default=None,
    )
    posisi = (cv.profil or {}).get("posisi") if cv else None
    return [posisi] if posisi else []


def _lokasi(user: User) -> list[str]:
    pref = user.preferensi
    return list(pref.lokasi) if pref and pref.lokasi else [LOKASI_DEFAULT]


def _unik(nilai: list[str], batas: int) -> list[str]:
    return list(dict.fromkeys(n.strip() for n in nilai if n.strip()))[:batas]


def tarik(db: Session, halaman: int = 1) -> HasilTarik:
    """Satu putaran penarikan untuk seluruh pengguna. Satu permintaan per kota."""
    pengguna = ambil_user_siap(db)

    kata_kunci = PEMISAH.join(_unik([k for u in pengguna for k in _kata_kunci(u)], MAKS_KATA_KUNCI))
    lokasi = _unik([lok for u in pengguna for lok in _lokasi(u)], MAKS_LOKASI)

    if not kata_kunci:
        logger.info("Tidak ada kata kunci — belum ada CV yang profilnya jadi")
        return HasilTarik(kata_kunci="", lokasi=lokasi, halaman=0, permintaan=0, dibaca=0, baru=0)

    permintaan = dibaca = baru = 0
    for kota in lokasi:
        for nomor in range(1, halaman + 1):
            if permintaan >= MAKS_PERMINTAAN:
                logger.warning("Berhenti di %s permintaan — rem kuota", permintaan)
                break

            try:
                jobs = search(kata_kunci, kota, halaman=nomor)
            except JoobleError as e:
                # kuota habis atau Jooble bermasalah — yang sudah masuk tetap dipakai
                logger.warning("Penarikan %s halaman %s gagal: %s", kota, nomor, e)
                break

            permintaan += 1
            dibaca += len(jobs)
            baru += simpan_lowongan(db, jobs)

    return HasilTarik(
        kata_kunci=kata_kunci,
        lokasi=lokasi,
        halaman=halaman,
        permintaan=permintaan,
        dibaca=dibaca,
        baru=baru,
    )
