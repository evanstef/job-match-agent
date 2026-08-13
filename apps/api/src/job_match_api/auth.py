from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from job_match_api.config import settings

MASA_BERLAKU_HARI = 7

# batas keras bcrypt: byte ke-73 dan seterusnya tidak ikut dihitung
MAKS_PASSWORD = 72


class AuthError(Exception):
    """Kredensial tidak sah."""


def hash_password(password: str) -> str:
    sandi = password.encode()
    if len(sandi) > MAKS_PASSWORD:
        raise AuthError(f"Password maksimal {MAKS_PASSWORD} karakter")
    return bcrypt.hashpw(sandi, bcrypt.gensalt()).decode()


def cocok_password(password: str, hash_tersimpan: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hash_tersimpan.encode())
    except ValueError:
        # hash rusak atau password kepanjangan — dianggap tidak cocok, bukan error server
        return False


def buat_token(user_id: int) -> str:
    sekarang = datetime.now(UTC)
    isi = {
        "sub": str(user_id),
        "iat": sekarang,
        "exp": sekarang + timedelta(days=MASA_BERLAKU_HARI),
    }
    return jwt.encode(isi, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def baca_token(token: str) -> int:
    """Balikin user_id dari token. Lempar AuthError kalau tidak sah atau kedaluwarsa."""
    try:
        isi = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(isi["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as e:
        raise AuthError("Token tidak sah atau sudah kedaluwarsa") from e
