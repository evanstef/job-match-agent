import logging

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from job_match_api.api.errors import respons_error
from job_match_api.cv.pdf import PdfError, ekstrak_teks
from job_match_api.cv.profil import ProfilCv, ProfilError, ekstrak_profil
from job_match_api.db.models import User
from job_match_api.db.repository import simpan_cv, simpan_profil
from job_match_api.db.session import DbSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["cv"])

MAKS_UKURAN = 5 * 1024 * 1024  # 5 MB
MAKS_NAMA_FILE = 255


class UploadCvOut(BaseModel):
    id_cv: int
    panjang_teks: int
    profil: ProfilCv | None


@router.post(
    "/upload",
    responses=respons_error(
        (400, "File PDF tidak bisa dibaca"),
        (404, "User tidak ditemukan"),
    ),
)
def upload_cv(user_id: int, file: UploadFile, db: DbSession) -> UploadCvOut:
    """Terima CV berbentuk PDF, ambil teksnya, simpan sebagai versi baru."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "File harus berbentuk PDF")

    # dibaca sebatas MAKS_UKURAN + 1 supaya file raksasa tidak masuk memori dulu
    data = file.file.read(MAKS_UKURAN + 1)
    if len(data) > MAKS_UKURAN:
        raise HTTPException(400, "Ukuran file maksimal 5 MB")

    if db.get(User, user_id) is None:
        raise HTTPException(404, f"User {user_id} tidak ditemukan")

    try:
        teks = ekstrak_teks(data)
    except PdfError as e:
        raise HTTPException(400, str(e)) from e

    cv = simpan_cv(db, user_id, teks, (file.filename or "")[:MAKS_NAMA_FILE])

    # profil boleh gagal — CV tetap tersimpan, tinggal diproses ulang nanti
    profil = None
    try:
        profil = ekstrak_profil(teks)
        simpan_profil(db, cv, profil.model_dump())
    except (ProfilError, SQLAlchemyError) as e:
        db.rollback()
        profil = None
        logger.warning("Profil CV %s gagal dibuat: %s", cv.id, e)

    return UploadCvOut(id_cv=cv.id, panjang_teks=len(teks), profil=profil)
