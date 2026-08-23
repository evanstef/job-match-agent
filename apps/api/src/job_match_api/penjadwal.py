import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from job_match_api.config import settings
from job_match_api.db.repository import ambil_user_siap
from job_match_api.db.session import SessionLocal
from job_match_api.pengaya import lengkapi
from job_match_api.pengisi import isi_vektor
from job_match_api.pengumpul import tarik
from job_match_api.putaran import jalankan_dan_kirim

logger = logging.getLogger(__name__)

# WAJIB dipatok: server jalan di UTC, hour="9" polos berarti 16.00 WIB
JAM = "9,13"
ZONA = "Asia/Jakarta"

# Dipatok kuota, bukan selera: Groq gratis 200.000 token/hari, satu penilaian ~2.000.
# 20 x 2 putaran = 80.000, masih longgar. Yang kepotong adalah yang paling jauh dari CV.
MAKS_DINILAI = 20

# 100 lowongan per halaman; berapa banyak yang benar-benar tertarik dibatasi
# MAKS_PERMINTAAN di pengumpul, bukan angka ini
HALAMAN = 3

_penjadwal = BackgroundScheduler(timezone=ZONA)


def _isi_kolam(db: Session) -> None:
    """Tiga langkah pengisi bahan sebelum penilaian: tarik, hitung vektor, lengkapi isi."""
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
        # penarikan gagal bukan alasan melewatkan penilaian — lowongan lama masih ada
        logger.exception("Penarikan lowongan gagal")

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
