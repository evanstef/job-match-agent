import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from job_match_api.config import settings
from job_match_api.db.models import Cv
from job_match_api.db.session import SessionLocal
from job_match_api.putaran import jalankan_dan_kirim

logger = logging.getLogger(__name__)

# WAJIB dipatok: server jalan di UTC, hour="8" polos berarti 15.00 WIB
JAM = "8,15,21"
ZONA = "Asia/Jakarta"

# cron menilai semua kandidat; pemotongan cuma rem darurat kalau jumlahnya meledak
MAKS_DINILAI = 100

_penjadwal = BackgroundScheduler(timezone=ZONA)


def _putaran_semua_user() -> None:
    db = SessionLocal()
    try:
        stmt = select(Cv.user_id).where(Cv.profil.is_not(None)).distinct()
        for user_id in db.execute(stmt).scalars().all():
            try:
                hasil = jalankan_dan_kirim(db, user_id, MAKS_DINILAI)
                logger.info(
                    "User %s: %s kandidat, %s dinilai, %s gagal, %s terkirim",
                    user_id,
                    hasil.kandidat,
                    hasil.dinilai,
                    hasil.gagal,
                    len(hasil.terpilih),
                )
            except Exception:
                # satu user bermasalah tidak boleh menghentikan putaran user lain
                logger.exception("Putaran gagal untuk user %s", user_id)
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
