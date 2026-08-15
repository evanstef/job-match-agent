from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from job_match_api.api.deps import PenggunaSekarang
from job_match_api.api.errors import respons_error
from job_match_api.db.repository import simpan_preferensi
from job_match_api.db.session import DbSession
from job_match_api.delivery.whatsapp import KurirError, normalkan_nomor

router = APIRouter(prefix="/preferensi", tags=["preferensi"])

# batas kuota, bukan batas desain: sumber data hanya menerima satu lokasi per permintaan
MAKS_LOKASI = 3


class PreferensiIn(BaseModel):
    lokasi: list[str] = []
    bersedia_relokasi: bool = False
    mau_remote: bool = False
    whatsapp: str | None = None


class PreferensiOut(BaseModel):
    lokasi: list[str]
    bersedia_relokasi: bool
    mau_remote: bool
    whatsapp: str | None


@router.get("", responses=respons_error((401, "Belum masuk")))
def lihat(pengguna: PenggunaSekarang) -> PreferensiOut:
    """Preferensi yang tersimpan. Kosong kalau belum pernah diisi."""
    pref = pengguna.preferensi
    if pref is None:
        return PreferensiOut(lokasi=[], bersedia_relokasi=False, mau_remote=False, whatsapp=None)

    return PreferensiOut(
        lokasi=pref.lokasi,
        bersedia_relokasi=pref.bersedia_relokasi,
        mau_remote=pref.mau_remote,
        whatsapp=pref.whatsapp,
    )


@router.post(
    "",
    responses=respons_error(
        (400, "Isian preferensi tidak sah"),
        (401, "Belum masuk"),
    ),
)
def simpan(masukan: PreferensiIn, pengguna: PenggunaSekarang, db: DbSession) -> PreferensiOut:
    """Simpan preferensi. Menimpa yang lama, bukan menambah baris baru."""
    lokasi = [k.strip() for k in masukan.lokasi if k.strip()]
    if len(lokasi) > MAKS_LOKASI:
        raise HTTPException(400, f"Maksimal {MAKS_LOKASI} kota")

    nomor = None
    if masukan.whatsapp:
        try:
            nomor = normalkan_nomor(masukan.whatsapp)
        except KurirError as e:
            raise HTTPException(400, str(e)) from e

    pref = simpan_preferensi(
        db, pengguna.id, lokasi, masukan.bersedia_relokasi, masukan.mau_remote, nomor
    )
    return PreferensiOut(
        lokasi=pref.lokasi,
        bersedia_relokasi=pref.bersedia_relokasi,
        mau_remote=pref.mau_remote,
        whatsapp=pref.whatsapp,
    )
