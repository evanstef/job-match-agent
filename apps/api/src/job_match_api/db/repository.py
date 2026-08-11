from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from job_match_api.db.models import Cv, Lowongan, LowonganTerkirim
from job_match_api.sources.jooble import JoobleJob


def simpan_lowongan(db: Session, jobs: list[JoobleJob]) -> int:
    if not jobs:
        return 0

    stmt = insert(Lowongan).values([job.model_dump() for job in jobs])
    stmt = stmt.on_conflict_do_nothing(index_elements=["id"]).returning(Lowongan.id)

    hasil = db.execute(stmt).scalars().all()
    db.commit()
    return len(hasil)


# logic simpan cv
def simpan_cv(db: Session, user_id: int, teks: str, nama_file: str | None) -> Cv:
    cv = Cv(user_id=user_id, teks_mentah=teks, nama_file=nama_file)
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


# logic untuk simpan profil
def simpan_profil(db: Session, cv: Cv, profil: dict) -> Cv:
    cv.profil = profil
    cv.profil_at = func.clock_timestamp()
    db.commit()
    db.refresh(cv)
    return cv


# CV terakhir yang profilnya sudah jadi — yang gagal diproses LLM dilewati
def ambil_cv_terbaru(db: Session, user_id: int) -> Cv | None:
    stmt = (
        select(Cv)
        .where(Cv.user_id == user_id, Cv.profil.is_not(None))
        .order_by(Cv.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


# lowongan yang belum pernah dinilai untuk user ini
def ambil_lowongan_belum_dinilai(db: Session, user_id: int) -> list[Lowongan]:
    sudah = select(LowonganTerkirim).where(
        LowonganTerkirim.user_id == user_id,
        LowonganTerkirim.lowongan_id == Lowongan.id,
    )
    # terbaru dulu — kalau harus dipotong, yang tersisih yang paling basi, bukan yang acak
    stmt = select(Lowongan).where(~sudah.exists()).order_by(Lowongan.updated.desc().nulls_last())
    return list(db.execute(stmt).scalars().all())


# catat hasil penilaian: (lowongan_id, verdict, skor)
def catat_penilaian(db: Session, user_id: int, penilaian: Iterable[tuple[int, str, int]]) -> int:
    baris = [
        {"user_id": user_id, "lowongan_id": lowongan_id, "verdict": verdict, "skor": skor}
        for lowongan_id, verdict, skor in penilaian
    ]
    if not baris:
        return 0

    stmt = insert(LowonganTerkirim).values(baris)
    stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "lowongan_id"]).returning(
        LowonganTerkirim.id
    )

    hasil = db.execute(stmt).scalars().all()
    db.commit()
    return len(hasil)
