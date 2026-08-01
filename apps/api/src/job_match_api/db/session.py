from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from job_match_api.config import settings
from collections.abc import Generator


# bikin engine untuk connect ke database
engine = create_engine(settings.database_url, pool_pre_ping=True)

# bikin session untuk connect ke database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# bikin dependency untuk get session
def get_db() -> Generator[Session, None, None]:
    """Dependency FastAPI — buka session per request, tutup otomatis."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
