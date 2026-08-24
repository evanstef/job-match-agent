import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from job_match_api.config import settings
from job_match_api.db.repository import ambil_user_siap
from job_match_api.db.session import SessionLocal
from job_match_api.pengaya import lengkapi
from job_match_api.pengisi import isi_vektor
from job_match_api.pengumpul import tarik, tarik_glints
from job_match_api.putaran import jalankan_dan_kirim

logger = logging.getLogger(__name__)

# WAJIB dipatok: server jalan di UTC, hour="9" polos berarti 16.00 WIB
JAM = "9,13"
ZONA = "Asia/Jakarta"

# Dipatok kuota, bukan selera: Groq gratis 200.000 token/hari. Satu penilaian
# sekarang ULANGAN=3 panggilan x ~2.000 token = ~6.000 (dulu satu panggilan saja).
# 15 x 2 putaran x 6.000 = 180.000, masih di bawah jatah. Yang kepotong adalah
# yang paling jauh dari CV.
MAKS_DINILAI = 15

# Hanya dipakai jalur Jooble (_isi_kolam_jooble). 100 lowongan per halaman;
# berapa banyak yang benar-benar tertarik dibatasi MAKS_PERMINTAAN di pengumpul,
# bukan angka ini
HALAMAN = 3

_penjadwal = BackgroundScheduler(timezone=ZONA)


def _isi_kolam(db: Session) -> None:
    """Dua langkah pengisi bahan sebelum penilaian: tarik dari scraper, hitung vektor."""
    try:
        hasil = tarik_glints(db)
        logger.info(
            "Tarik Glints: %s dibaca, %s baru (%s)",
            hasil.dibaca,
            hasil.baru,
            ", ".join(hasil.kata_kunci),
        )
    except Exception:
        # penarikan gagal bukan alasan melewatkan penilaian — lowongan lama masih ada
        logger.exception("Penarikan Glints gagal")

    try:
        hasil = isi_vektor(db)
        logger.info(
            "Vektor: %s diperiksa, %s berhasil, %s gagal",
            hasil.diperiksa,
            hasil.berhasil,
            hasil.gagal,
        )
    except Exception:
        logger.exception("Pengisian vektor gagal")


def _isi_kolam_jooble(db: Session) -> None:
    """LEGACY — tidak dipanggil sejak 23 Agu 2026, digantikan scraper Glints.

    Dibiarkan sebagai fungsi utuh, bukan dikomentari, supaya tetap ikut diperiksa
    lint dan tidak diam-diam basi kalau tanda tangan tarik() atau lengkapi()
    berubah. Menghidupkannya lagi cukup dengan memanggilnya dari _isi_kolam.

    lengkapi() ikut dimatikan di sini karena hanya melayani baris Jooble:
    antreannya disaring ke sumber ATS, sedangkan lowongan Glints sudah membawa
    isi lengkapnya sendiri sejak masuk.

    ⚠️ Kalau dihidupkan lagi, ingat urutannya: isi_vektor menghitung vektor dari
    isi_lengkap, tapi di jalur ini isi_lengkap baru datang di lengkapi() —
    sesudahnya. Baris yang vektornya terlanjur dihitung tidak pernah dihitung
    ulang, jadi vektornya akan lahir dari cuplikan saja.
    """
    try:
        hasil = tarik(db, halaman=HALAMAN)
        logger.info(
            "Tarik: %s permintaan, %s dibaca, %s baru (%s | %s)",
            hasil.permintaan,
            hasil.dibaca,
            hasil.baru,
            hasil.kata_kunci,
            ", ".join(hasil.lokasi),
        )
    except Exception:
        logger.exception("Penarikan lowongan gagal")

    try:
        hasil = lengkapi(db)
        logger.info(
            "Lengkapi: %s diperiksa, %s berhasil, %s gagal",
            hasil.diperiksa,
            hasil.berhasil,
            hasil.gagal,
        )
    except Exception:
        # isi lengkap cuma pelengkap — tanpa itu penilaian tetap jalan dari cuplikan
        logger.exception("Pelengkapan isi lowongan gagal")


def _putaran_semua_user() -> None:
    db = SessionLocal()
    try:
        _isi_kolam(db)

        for pengguna in ambil_user_siap(db):
            try:
                hasil = jalankan_dan_kirim(db, pengguna.id, MAKS_DINILAI)
                logger.info(
                    "User %s: %s kandidat, %s dinilai, %s gagal, %s terkirim",
                    pengguna.id,
                    hasil.kandidat,
                    hasil.dinilai,
                    hasil.gagal,
                    len(hasil.terpilih),
                )
            except Exception:
                # satu user bermasalah tidak boleh menghentikan putaran user lain
                logger.exception("Putaran gagal untuk user %s", pengguna.id)
    finally:
        db.close()


def mulai() -> None:
    if not settings.penjadwal_aktif:
        logger.info("Penjadwal dimatikan (PENJADWAL_AKTIF=false)")
        return

    _penjadwal.add_job(
        _putaran_semua_user,
        CronTrigger(hour=JAM, timezone=ZONA),
        id="putaran-harian",
        replace_existing=True,
    )
    _penjadwal.start()
    logger.info("Penjadwal hidup — jam %s %s", JAM, ZONA)


def berhenti() -> None:
    if _penjadwal.running:
        _penjadwal.shutdown(wait=False)
