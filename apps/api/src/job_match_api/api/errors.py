import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from job_match_api.config import settings

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Bentuk baku semua respons error — dipakai juga untuk dokumentasi OpenAPI."""

    sukses: bool = False
    errors: list[str]


# ditempel ke tiap route: responses={**RESPONS_ERROR, 404: {...}}
RESPONS_ERROR: dict[int | str, dict] = {
    400: {"model": ErrorResponse, "description": "Input tidak valid"},
    500: {"model": ErrorResponse, "description": "Kesalahan tak terduga di server"},
}


def respons_error(*kode_dan_deskripsi: tuple[int, str]) -> dict[int | str, dict]:
    """Gabungkan RESPONS_ERROR dengan kode tambahan khusus route tertentu."""
    tambahan = {
        kode: {"model": ErrorResponse, "description": desc} for kode, desc in kode_dan_deskripsi
    }
    return {**RESPONS_ERROR, **tambahan}


# terjemahan tipe error Pydantic ke bahasa yang dimengerti orang biasa
PESAN = {
    "missing": "wajib diisi",
    "string_type": "harus berupa teks",
    "string_too_short": "terlalu pendek",
    "string_too_long": "terlalu panjang",
    "int_parsing": "harus berupa angka",
    "int_type": "harus berupa angka",
    "float_parsing": "harus berupa angka",
    "bool_parsing": "harus true atau false",
    "datetime_parsing": "format tanggalnya tidak dikenali",
    "datetime_from_date_parsing": "format tanggalnya tidak dikenali",
    "url_parsing": "bukan URL yang valid",
    "enum": "pilihannya tidak tersedia",
    "too_short": "jumlahnya terlalu sedikit",
    "too_long": "jumlahnya terlalu banyak",
    "greater_than": "nilainya terlalu kecil",
    "less_than": "nilainya terlalu besar",
    "value_error": "nilainya tidak valid",
}


def _jadikan_kalimat(err: dict) -> str:
    """Ubah satu error Pydantic jadi satu kalimat yang bisa dibaca pengguna."""
    # 'body'/'query'/'path' cuma penanda teknis, bukan nama field
    bagian = [str(x) for x in err.get("loc", ()) if x not in ("body", "query", "path")]
    field = " → ".join(bagian) or "data"
    return f"'{field}' {PESAN.get(err.get('type', ''), err.get('msg', 'tidak valid'))}"


def _buang_422_dari_dokumentasi(app: FastAPI) -> None:
    """
    FastAPI otomatis menulis 422 di OpenAPI, padahal validasi sudah kita ubah jadi 400.
    Skema dibersihkan setelah digenerate supaya dokumentasi tidak berbohong.
    """

    def openapi_bersih() -> dict:
        if app.openapi_schema:
            return app.openapi_schema

        skema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        for operasi in skema.get("paths", {}).values():
            for detail in operasi.values():
                detail.get("responses", {}).pop("422", None)

        komponen = skema.get("components", {}).get("schemas", {})
        komponen.pop("HTTPValidationError", None)
        komponen.pop("ValidationError", None)

        app.openapi_schema = skema
        return skema

    app.openapi = openapi_bersih


def pasang_error_handler(app: FastAPI) -> None:
    """Satu tempat untuk semua respons error, supaya bentuknya seragam."""

    _buang_422_dari_dokumentasi(app)

    @app.exception_handler(RequestValidationError)
    async def _validasi(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "sukses": False,
                "errors": [_jadikan_kalimat(e) for e in exc.errors()],
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"sukses": False, "errors": [str(exc.detail)]},
        )

    @app.exception_handler(Exception)
    async def _tak_terduga(request: Request, exc: Exception) -> JSONResponse:
        # traceback lengkap ke log server, bukan ke pengguna
        logger.exception("Error tak tertangani di %s %s", request.method, request.url.path)

        pesan = (
            f"{type(exc).__name__}: {exc}"
            if settings.app_env == "development"
            else "Terjadi kesalahan di server"
        )
        return JSONResponse(status_code=500, content={"sukses": False, "errors": [pesan]})
