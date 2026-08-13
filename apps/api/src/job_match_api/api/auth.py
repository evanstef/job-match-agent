import logging

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from job_match_api.api.errors import respons_error
from job_match_api.auth import (
    MASA_BERLAKU_HARI,
    AuthError,
    buat_token,
    cocok_password,
    hash_password,
)
from job_match_api.config import settings
from job_match_api.db.repository import cari_user_by_email, simpan_user
from job_match_api.db.session import DbSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

MIN_PASSWORD = 8
NAMA_COOKIE = "token"
UMUR_COOKIE = MASA_BERLAKU_HARI * 24 * 60 * 60


class Kredensial(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    token: str


def _pasang_cookie(respons: Response, token: str) -> None:
    respons.set_cookie(
        NAMA_COOKIE,
        token,
        max_age=UMUR_COOKIE,
        httponly=True,
        samesite="lax",
        secure=settings.app_env != "development",
    )


@router.post("/daftar", responses=respons_error((409, "Email sudah terdaftar")))
def daftar(kredensial: Kredensial, respons: Response, db: DbSession) -> TokenOut:
    """Bikin akun baru, langsung dapat token."""
    email = kredensial.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Email tidak sah")
    if len(kredensial.password) < MIN_PASSWORD:
        raise HTTPException(400, f"Password minimal {MIN_PASSWORD} karakter")

    if cari_user_by_email(db, email):
        raise HTTPException(409, "Email sudah terdaftar")

    try:
        sandi = hash_password(kredensial.password)
    except AuthError as e:
        raise HTTPException(400, str(e)) from e

    user = simpan_user(db, email, sandi)
    token = buat_token(user.id)
    _pasang_cookie(respons, token)
    return TokenOut(token=token)


@router.post("/masuk", responses=respons_error((401, "Email atau password salah")))
def masuk(kredensial: Kredensial, respons: Response, db: DbSession) -> TokenOut:
    """Tukar email + password dengan token."""
    email = kredensial.email.strip().lower()
    user = cari_user_by_email(db, email)

    # alasan aslinya cuma ke log — pesan ke pengguna sengaja sama supaya
    # tidak bisa dipakai menebak email mana yang terdaftar
    if user is None:
        logger.info("Gagal masuk: email %s tidak terdaftar", email)
        raise HTTPException(401, "Email atau password salah")
    if not cocok_password(kredensial.password, user.password_hash):
        logger.info("Gagal masuk: password salah untuk user %s", user.id)
        raise HTTPException(401, "Email atau password salah")

    token = buat_token(user.id)
    _pasang_cookie(respons, token)
    return TokenOut(token=token)
