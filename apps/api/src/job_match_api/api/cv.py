import logging

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from job_match_api.api.errors import respons_error
from job_match_api.cv.pdf import PdfError, ekstrak_teks
from job_match_api.cv.profil import ProfilCv, ProfilError, ekstrak_profil
from job_match_api.db.repository import simpan_cv, simpan_profil
from job_match_api.db.session import DbSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["cv"])

MAKS_UKURAN = 5 * 1024 * 1024  # 5 MB


class UploadCvOut(BaseModel):
    id_cv: int
    panjang_teks: int
    profil: ProfilCv | None


@router.post("/upload", responses=respons_error((400, "File PDF tidak bisa dibaca")))
def upload_cv(user_id: int, file: UploadFile, db: DbSession) -> UploadCvOut:
    """Terima CV berbentuk PDF, ambil teksnya, simpan sebagai versi baru."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "File harus berbentuk PDF")

    data = file.file.read()
    if len(data) > MAKS_UKURAN:
        raise HTTPException(400, "Ukuran file maksimal 5 MB")

    try:
        teks = ekstrak_teks(data)
    except PdfError as e:
        raise HTTPException(400, str(e)) from e

    cv = simpan_cv(db, user_id, teks, file.filename)

    # ekstrak profile dari CV menjadi json text menggunakan LLM
    profil = None
    try:
        profil = ekstrak_profil(teks)
        simpan_profil(db, cv, profil.model_dump())
    except ProfilError as e:
        logger.warning("Profil CV %s gagal dibuat: %s", cv.id, e)

    return UploadCvOut(id_cv=cv.id, panjang_teks=len(teks), profil=profil)
