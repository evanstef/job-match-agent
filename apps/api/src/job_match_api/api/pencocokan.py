from fastapi import APIRouter, HTTPException

from job_match_api.api.deps import PenggunaSekarang
from job_match_api.api.errors import respons_error
from job_match_api.db.session import DbSession
from job_match_api.pipeline import HasilJalan, PipelineError
from job_match_api.putaran import jalankan_dan_kirim

router = APIRouter(prefix="/pencocokan", tags=["pencocokan"])


@router.post(
    "/jalankan",
    responses=respons_error(
        (401, "Belum masuk"),
        (404, "Belum punya CV yang profilnya sudah jadi"),
    ),
)
def jalankan_pencocokan(
    pengguna: PenggunaSekarang, db: DbSession, maks_dinilai: int = 10
) -> HasilJalan:
    """Jalankan satu putaran manual: nilai, kirim yang layak, balikin ringkasannya."""
    try:
        return jalankan_dan_kirim(db, pengguna.id, maks_dinilai)
    except PipelineError as e:
        raise HTTPException(404, str(e)) from e
