from fastapi import FastAPI

from job_match_api.api import cv, lowongan, pencocokan
from job_match_api.api.errors import pasang_error_handler
from job_match_api.config import settings

app = FastAPI(
    title="Job Match Agent API",
    version="0.1.0",
)

# semua respons error lewat satu tempat, bentuknya seragam
pasang_error_handler(app)

# API route untuk semua endpoint yang berhubungan dengan lowongan
app.include_router(lowongan.router)

# API route untuk semua endpoint yang berhubungan dengan cv
app.include_router(cv.router)

# API route untuk menjalankan pencocokan CV dengan lowongan
app.include_router(pencocokan.router)


# Endpoint untuk health check
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
