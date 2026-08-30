from collections.abc import Iterable

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from job_match_api.db.models import Cv, Lowongan, LowonganTerkirim, Preferensi, User
from job_match_api.sources.glints import GlintsJob
from job_match_api.sources.jooble import PENARIK as PENARIK_JOOBLE
from job_match_api.sources.jooble import JoobleJob

# Batas jarak kosinus CV -> lowongan. Menggantikan aturan cocok-cocokan kata yang
# dulu ada di saring_kasar. Diukur 2026-08-19: di bawah 0,60 masih bidang teknis,
# di atasnya mulai Operations/Sales/HR Manager.
JARAK_MAKS = 0.60


def cari_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


# hanya user yang CV-nya sudah terbaca yang bisa dicarikan lowongan.
def ambil_user_siap(db: Session) -> list[User]:
    stmt = (
        select(User)
        .join(Cv, Cv.user_id == User.id)
        .where(Cv.profil.is_not(None))
        .distinct()
        .order_by(User.id)
    )
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


def simpan_lowongan(
    db: Session, jobs: list[JoobleJob] | list[GlintsJob], penarik: str = PENARIK_JOOBLE
) -> int:
    if not jobs:
        return 0

    baris = []
    for job in jobs:
        nilai = job.model_dump()
        # id dari sumber turun jadi penanda asal; id baris sekarang dibuat sendiri
        nilai["id_penarik"] = str(nilai.pop("id"))
        nilai["penarik"] = penarik
        baris.append(nilai)

    stmt = insert(Lowongan).values(baris)
    stmt = stmt.on_conflict_do_nothing(index_elements=["penarik", "id_penarik"]).returning(
        Lowongan.id
    )

    hasil = db.execute(stmt).scalars().all()
    db.commit()
    return len(hasil)


# Satu user satu baris CV: yang lama ditimpa, bukan ditumpuk.
#
# Dipanggil HANYA setelah profil berhasil dibaca. Dulu CV disimpan lebih dulu lalu
# profilnya menyusul, dengan alasan "bisa diproses ulang nanti" — tapi tidak ada
# satu pun kode yang mencari CV tanpa profil, dan ambil_cv_terbaru justru
# menyaringnya. Jadi baris seperti itu tidak pernah terpakai, cuma menumpuk.
def simpan_cv_lengkap(
    db: Session,
    user_id: int,
    teks: str,
    nama_file: str | None,
    profil: dict,
    embedding: list[float] | None = None,
) -> Cv:
    cv = db.execute(
        select(Cv).where(Cv.user_id == user_id).order_by(Cv.id.desc()).limit(1)
    ).scalar_one_or_none()

    if cv is None:
        cv = Cv(user_id=user_id)
        db.add(cv)

    cv.teks_mentah = teks
    cv.nama_file = nama_file
    cv.profil = profil
    cv.profil_at = func.clock_timestamp()
    # None di sini berarti "kosongkan", bukan "jangan diubah": profilnya berganti,
    # jadi vektor lama sudah tidak mewakili apa-apa dan lebih baik hilang.
    # pipeline._vektor_cv yang akan menghitungnya lagi di putaran berikutnya.
    cv.embedding = embedding

    db.commit()
    db.refresh(cv)
    return cv


def simpan_vektor_cv(db: Session, cv: Cv, vektor: list[float]) -> Cv:
    cv.embedding = vektor
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


# lowongan yang belum pernah dinilai untuk user ini, terdekat dengan CV lebih dulu
def ambil_lowongan_belum_dinilai(
    db: Session, user_id: int, vektor_cv: list[float] | None = None
) -> list[Lowongan]:
    sudah = select(LowonganTerkirim).where(
        LowonganTerkirim.user_id == user_id,
        LowonganTerkirim.lowongan_id == Lowongan.id,
    )
    stmt = select(Lowongan).where(~sudah.exists())

    if vektor_cv is None:
        return list(db.execute(stmt.order_by(Lowongan.id.desc())).scalars().all())

    jarak = Lowongan.embedding.cosine_distance(vektor_cv)
    stmt = stmt.where(jarak < JARAK_MAKS).order_by(jarak)
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


# lowongan yang vektornya belum dihitung.
# urut id menaik: yang paling lama menunggu didahulukan. Kalau dibalik jadi terbaru
# dulu, tumpukan lama tidak pernah kebagian selama tiap putaran ada lowongan baru.
def ambil_lowongan_tanpa_vektor(db: Session, batas: int) -> list[Lowongan]:
    stmt = select(Lowongan).where(Lowongan.embedding.is_(None)).order_by(Lowongan.id).limit(batas)
    return list(db.execute(stmt).scalars().all())


def simpan_vektor_lowongan(db: Session, vektor: Iterable[tuple[int, list[float]]]) -> int:
    jumlah = 0
    for lowongan_id, angka in vektor:
        stmt = update(Lowongan).where(Lowongan.id == lowongan_id).values(embedding=angka)
        jumlah += db.execute(stmt).rowcount
    db.commit()
    return jumlah


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
