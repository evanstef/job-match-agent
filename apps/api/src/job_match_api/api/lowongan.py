from pathlib import Path

from fastapi import APIRouter, HTTPException

from job_match_api.api.errors import respons_error
from job_match_api.db.repository import simpan_lowongan
from job_match_api.db.session import DbSession
from job_match_api.sources.jooble import JoobleError, baca_dari_file, search

router = APIRouter(prefix="/lowongan", tags=["lowongan"])

DATA_DIR = Path(__file__).resolve().parents[5] / "data"


# impor data dari file sample
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


# tarik data dari jooble
@router.post("/tarik", responses=respons_error((502, "Gagal tarik data dari Jooble (Bad Gateway)")))
def tarik_jooble(keywords: str, location: str, db: DbSession) -> dict[str, int]:
    """Tarik lowongan langsung dari API Jooble lalu simpan (dedup otomatis)."""
    try:
        jobs = search(keywords, location)
    except JoobleError as e:
        raise HTTPException(status_code=502, detail=f"Gagal tarik data dari Jooble: {e}") from e

    masuk = simpan_lowongan(db, jobs)
    return {"dibaca": len(jobs), "baru_masuk": masuk}
