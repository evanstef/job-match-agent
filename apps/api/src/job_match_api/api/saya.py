from fastapi import APIRouter, Response
from pydantic import BaseModel

from job_match_api.api.auth import NAMA_COOKIE
from job_match_api.api.deps import PenggunaSekarang
from job_match_api.api.errors import respons_error

router = APIRouter(prefix="/auth", tags=["auth"])


class SayaOut(BaseModel):
    id: int
    email: str
    punya_cv: bool
    punya_preferensi: bool


@router.get("/saya", responses=respons_error((401, "Belum masuk")))
def saya(pengguna: PenggunaSekarang) -> SayaOut:
    """Dipakai frontend untuk tahu status login — cookie httpOnly tidak terbaca JavaScript."""
    return SayaOut(
        id=pengguna.id,
        email=pengguna.email,
        punya_cv=any(cv.profil is not None for cv in pengguna.cvs),
        punya_preferensi=pengguna.preferensi is not None,
    )


@router.post("/keluar")
def keluar(respons: Response) -> dict[str, bool]:
    """Hapus cookie. Token yang sudah beredar tetap sah sampai kedaluwarsa."""
    respons.delete_cookie(NAMA_COOKIE)
    return {"sukses": True}
