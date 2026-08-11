from fastapi import APIRouter, HTTPException

from job_match_api.api.errors import respons_error
from job_match_api.db.session import DbSession
from job_match_api.pipeline import HasilJalan, PipelineError, jalankan

router = APIRouter(prefix="/pencocokan", tags=["pencocokan"])


@router.post(
    "/jalankan",
    responses=respons_error((404, "User belum punya CV yang profilnya sudah jadi")),
)
def jalankan_pencocokan(user_id: int, db: DbSession, maks_dinilai: int = 10) -> HasilJalan:
    """Nilai lowongan yang belum pernah dinilai untuk user ini, balikin yang layak dikirim."""
    try:
        return jalankan(db, user_id, maks_dinilai)
    except PipelineError as e:
        raise HTTPException(404, str(e)) from e
