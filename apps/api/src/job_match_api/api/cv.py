import logging

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from job_match_api.api.deps import PenggunaSekarang
from job_match_api.api.errors import respons_error
from job_match_api.cv.pdf import PdfError, ekstrak_teks
from job_match_api.cv.profil import ProfilCv, ProfilError, ekstrak_profil
from job_match_api.db.repository import simpan_cv_lengkap
from job_match_api.db.session import DbSession
from job_match_api.vektor import VektorError, dari_profil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["cv"])

MAKS_UKURAN = 5 * 1024 * 1024  # 5 MB
MAKS_NAMA_FILE = 255
MAKS_TEKS = 200_000


class BacaCvOut(BaseModel):
    nama_file: str
    teks: str
    profil: ProfilCv


class SimpanCvIn(BaseModel):
    nama_file: str = Field(max_length=MAKS_NAMA_FILE)
    teks: str = Field(min_length=1, max_length=MAKS_TEKS)
    profil: ProfilCv


class SimpanCvOut(BaseModel):
    id_cv: int
    panjang_teks: int
    profil: ProfilCv


def _teks_dari_pdf(file: UploadFile) -> str:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "File harus berbentuk PDF")

    # dibaca sebatas MAKS_UKURAN + 1 supaya file raksasa tidak masuk memori dulu
    data = file.file.read(MAKS_UKURAN + 1)
    if len(data) > MAKS_UKURAN:
        raise HTTPException(400, "Ukuran file maksimal 5 MB")

    try:
        return ekstrak_teks(data)
    except PdfError as e:
        raise HTTPException(400, str(e)) from e


@router.post(
    "/baca",
    responses=respons_error(
        (400, "File PDF tidak bisa dibaca"),
        (401, "Belum masuk"),
        (422, "Isi CV tidak bisa dibaca"),
    ),
)
def baca_cv(file: UploadFile, pengguna: PenggunaSekarang) -> BacaCvOut:
    """Baca CV lalu kembalikan hasilnya. TIDAK menyimpan apa pun.

    Dipisah dari penyimpanan supaya pengguna bisa melihat — dan membetulkan —
    hasil bacaan sebelum memutuskan. Ganti berkas berkali-kali sebelum menekan
    Simpan tidak meninggalkan satu pun baris di database.
    """
    teks = _teks_dari_pdf(file)

    try:
        profil = ekstrak_profil(teks)
    except ProfilError as e:
        logger.warning("Profil CV user %s gagal dibaca: %s", pengguna.id, e)
        raise HTTPException(422, "Isi CV tidak bisa dibaca. Coba unggah berkas lain.") from e

    return BacaCvOut(
        nama_file=(file.filename or "")[:MAKS_NAMA_FILE],
        teks=teks,
        profil=profil,
    )


@router.post(
    "/simpan",
    responses=respons_error((401, "Belum masuk"), (500, "CV gagal disimpan")),
)
def simpan_cv(masukan: SimpanCvIn, pengguna: PenggunaSekarang, db: DbSession) -> SimpanCvOut:
    """Simpan hasil bacaan yang sudah dilihat pengguna. Tidak memanggil LLM lagi.

    Profil datang dari layar, bukan dihitung ulang — jadi kalau pengguna
    membetulkannya, yang tersimpan adalah versi yang sudah benar. Vektor sengaja
    dihitung di sini, bukan waktu membaca, supaya ikut versi yang dibetulkan itu.
    """
    isi = masukan.profil.model_dump()

    # embedding boleh gagal sendiri: profil dipakai OTAK untuk menilai, vektor cuma
    # untuk mengurutkan. Yang kedua hilang masih dihitung ulang pipeline._vektor_cv.
    vektor_profil = None
    try:
        vektor_profil = dari_profil(isi)
    except VektorError as e:
        logger.warning("Embedding CV user %s gagal: %s", pengguna.id, e)

    try:
        cv = simpan_cv_lengkap(db, pengguna.id, masukan.teks, masukan.nama_file, isi, vektor_profil)
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("CV user %s gagal disimpan", pengguna.id)
        raise HTTPException(500, "CV gagal disimpan") from e

    return SimpanCvOut(id_cv=cv.id, panjang_teks=len(masukan.teks), profil=masukan.profil)
