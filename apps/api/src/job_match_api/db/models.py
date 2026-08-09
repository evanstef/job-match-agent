from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from job_match_api.db.base import Base

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cvs: Mapped[list["Cv"]] = relationship(back_populates="user")
    telegram: Mapped["TelegramLink | None"] = relationship(back_populates="user")
    preferensi: Mapped["Preferensi | None"] = relationship(back_populates="user")


class Cv(Base):
    __tablename__ = "cv"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    teks_mentah: Mapped[str] = mapped_column(Text)
    nama_file: Mapped[str | None] = mapped_column(String(255))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    profil: Mapped[dict | None] = mapped_column(JSONB)
    profil_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="cvs")


class TelegramLink(Base):
    __tablename__ = "telegram_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    # dari /start di bot, bukan nomor HP
    chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tersambung_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="telegram")


class Preferensi(Base):
    __tablename__ = "preferensi"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    # maksimal 3 kota — dibatasi di aplikasi, bukan di skema
    lokasi: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list)
    bersedia_relokasi: Mapped[bool] = mapped_column(Boolean, default=False)
    mau_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="preferensi")


class Lowongan(Base):
    __tablename__ = "lowongan"

    # id dari Jooble: bigint, bisa negatif, 19 digit. Bukan punya kita.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    snippet: Mapped[str | None] = mapped_column(Text)
    salary: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(String(255), index=True)
    link: Mapped[str] = mapped_column(Text)
    updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    # diisi lapis 2; kosong artinya belum atau gagal diambil
    isi_lengkap: Mapped[str | None] = mapped_column(Text)
    isi_lengkap_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class LowonganTerkirim(Base):
    __tablename__ = "lowongan_terkirim"
    __table_args__ = (UniqueConstraint("user_id", "lowongan_id", name="uq_user_lowongan"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lowongan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lowongan.id", ondelete="CASCADE"), index=True
    )
    verdict: Mapped[str | None] = mapped_column(String(20))
    skor: Mapped[int | None] = mapped_column(Integer)
    dikirim: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    dikirim_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
