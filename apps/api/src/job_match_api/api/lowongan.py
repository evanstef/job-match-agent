from pathlib import Path

from fastapi import APIRouter, HTTPException

from job_match_api.api.errors import respons_error
from job_match_api.db.repository import simpan_lowongan
from job_match_api.db.session import DbSession
from job_match_api.sources.jooble import baca_dari_file

router = APIRouter(prefix="/lowongan", tags=["lowongan"])

DATA_DIR = Path(__file__).resolve().parents[5] / "data"


@router.post(
    "/impor-sample",
    responses=respons_error((404, "File sample tidak ada di folder data/")),
)
def impor_sample(nama_file: str, db: DbSession) -> dict[str, int]:
    """Impor lowongan dari file sample di folder data/ (dipakai selama pengembangan)."""
    path = (DATA_DIR / nama_file).resolve()

    # nama_file datang dari pengguna — pastikan tidak kabur keluar folder data/
    if not path.is_relative_to(DATA_DIR) or not path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{nama_file}' tidak ada di folder data/")

    jobs = baca_dari_file(path)
    masuk = simpan_lowongan(db, jobs)
    return {"dibaca": len(jobs), "baru_masuk": masuk}
