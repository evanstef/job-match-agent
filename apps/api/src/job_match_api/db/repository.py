from collections.abc import Iterable

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from job_match_api.db.models import Cv, Lowongan, LowonganTerkirim, Preferensi, User
from job_match_api.sources.jooble import JoobleJob


def cari_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


# hanya user yang CV-nya sudah terbaca yang bisa dicarikan lowongan
def ambil_user_siap(db: Session) -> list[User]:
    stmt = select(User).join(Cv, Cv.user_id == User.id).where(Cv.profil.is_not(None)).distinct()
    return list(db.execute(stmt).scalars().all())


def simpan_user(db: Session, email: str, password_hash: str) -> User:
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# satu user satu baris preferensi: dibuat kalau belum ada, ditimpa kalau sudah
def simpan_preferensi(
    db: Session,
    user_id: int,
    lokasi: list[str],
    bersedia_relokasi: bool,
    mau_remote: bool,
    whatsapp: str | None,
) -> Preferensi:
    pref = db.execute(select(Preferensi).where(Preferensi.user_id == user_id)).scalar_one_or_none()

    if pref is None:
        pref = Preferensi(user_id=user_id)
        db.add(pref)

    pref.lokasi = lokasi
    pref.bersedia_relokasi = bersedia_relokasi
    pref.mau_remote = mau_remote
    pref.whatsapp = whatsapp

    db.commit()
    db.refresh(pref)
    return pref


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


# lowongan yang isinya belum pernah diambil, dan sumbernya masih mungkin diambil
def ambil_lowongan_tanpa_isi(db: Session, sumber: list[str], batas: int) -> list[Lowongan]:
    stmt = (
        select(Lowongan)
        .where(
            Lowongan.isi_lengkap.is_(None),
            Lowongan.isi_lengkap_at.is_(None),
            Lowongan.source.in_(sumber),
            Lowongan.company.is_not(None),
        )
        .order_by(Lowongan.updated.desc().nulls_last())
        .limit(batas)
    )
    return list(db.execute(stmt).scalars().all())


def simpan_isi_lengkap(db: Session, isi: Iterable[tuple[int, str]]) -> int:
    jumlah = 0
    for lowongan_id, teks in isi:
        stmt = (
            update(Lowongan)
            .where(Lowongan.id == lowongan_id)
            .values(isi_lengkap=teks, isi_lengkap_at=func.clock_timestamp())
        )
        jumlah += db.execute(stmt).rowcount
    db.commit()
    return jumlah


# menandai bahwa sudah dicoba dan gagal, supaya tidak dicoba terus tiap putaran
def tandai_isi_gagal(db: Session, lowongan_ids: list[int]) -> int:
    if not lowongan_ids:
        return 0

    stmt = (
        update(Lowongan)
        .where(Lowongan.id.in_(lowongan_ids))
        .values(isi_lengkap_at=func.clock_timestamp())
    )
    hasil = db.execute(stmt)
    db.commit()
    return hasil.rowcount


# ditandai setelah pesannya benar-benar terkirim, bukan saat dinilai
def tandai_terkirim(db: Session, user_id: int, lowongan_ids: list[int]) -> int:
    if not lowongan_ids:
        return 0

    stmt = (
        update(LowonganTerkirim)
        .where(
            LowonganTerkirim.user_id == user_id,
            LowonganTerkirim.lowongan_id.in_(lowongan_ids),
        )
        .values(dikirim=True)
    )
    hasil = db.execute(stmt)
    db.commit()
    return hasil.rowcount
