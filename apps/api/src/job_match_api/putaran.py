import logging

from sqlalchemy.orm import Session

from job_match_api.config import settings
from job_match_api.db.repository import tandai_terkirim
from job_match_api.delivery.pesan import susun_pesan
from job_match_api.delivery.whatsapp import KurirError, kirim
from job_match_api.pipeline import HasilJalan, jalankan

logger = logging.getLogger(__name__)


def jalankan_dan_kirim(db: Session, user_id: int, maks_dinilai: int = 10) -> HasilJalan:
    """Satu putaran penuh: nilai lowongan, kirim yang layak, tandai yang sudah terkirim."""
    hasil = jalankan(db, user_id, maks_dinilai)
    if not hasil.terpilih:
        return hasil

    try:
        kirim(settings.whatsapp_tujuan, susun_pesan(hasil.terpilih))
    except KurirError as e:
        # penilaiannya sudah tercatat; yang gagal cuma pengirimannya, jadi bisa dicoba lagi nanti
        logger.warning("Gagal mengirim %s lowongan: %s", len(hasil.terpilih), e)
        return hasil

    tandai_terkirim(db, user_id, [low.id for low in hasil.terpilih])
    return hasil
