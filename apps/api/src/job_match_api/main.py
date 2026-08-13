from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from job_match_api import penjadwal
from job_match_api.api import auth, cv, lowongan, pencocokan, preferensi
from job_match_api.api.errors import pasang_error_handler
from job_match_api.config import settings


@asynccontextmanager
async def daur_hidup(_app: FastAPI) -> AsyncIterator[None]:
    penjadwal.mulai()
    yield
    penjadwal.berhenti()


app = FastAPI(
    title="Job Match Agent API",
    version="0.1.0",
    lifespan=daur_hidup,
)

# asalnya disebut spesifik dan allow_credentials dinyalakan
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.daftar_frontend,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# semua respons error lewat satu tempat, bentuknya seragam
pasang_error_handler(app)

# API route untuk daftar & masuk
app.include_router(auth.router)

# API route untuk semua endpoint yang berhubungan dengan lowongan
app.include_router(lowongan.router)

# API route untuk semua endpoint yang berhubungan dengan cv
app.include_router(cv.router)

# API route untuk preferensi pencarian & tujuan pengiriman
app.include_router(preferensi.router)

# API route untuk menjalankan pencocokan CV dengan lowongan
app.include_router(pencocokan.router)


# Endpoint untuk health check
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
