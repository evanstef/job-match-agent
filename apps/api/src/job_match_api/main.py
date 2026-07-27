from fastapi import FastAPI

from job_match_api.config import settings

app = FastAPI(
    title="Job Match Agent API",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
