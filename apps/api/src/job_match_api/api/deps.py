from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from job_match_api.api.auth import NAMA_COOKIE
from job_match_api.auth import AuthError, baca_token
from job_match_api.db.models import User
from job_match_api.db.session import DbSession

# auto_error=False supaya bisa jatuh ke cookie kalau header Authorization kosong
_bearer = HTTPBearer(auto_error=False)


def pengguna_sekarang(
    request: Request,
    db: DbSession,
    kredensial: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    """Siapa yang sedang masuk. Diambil dari token, tidak pernah dari parameter."""
    token = kredensial.credentials if kredensial else request.cookies.get(NAMA_COOKIE)
    if not token:
        raise HTTPException(401, "Belum masuk")

    try:
        user_id = baca_token(token)
    except AuthError as e:
        raise HTTPException(401, str(e)) from e

    # token bisa saja sah tapi akunnya sudah dihapus
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "Belum masuk")

    return user


PenggunaSekarang = Annotated[User, Depends(pengguna_sekarang)]
