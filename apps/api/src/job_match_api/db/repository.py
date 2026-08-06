from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from job_match_api.db.models import Cv, Lowongan
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
