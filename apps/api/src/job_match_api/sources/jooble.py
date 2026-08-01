from pydantic import BaseModel
from datetime import datetime
import json
from pathlib import Path

class JoobleJob(BaseModel):
    id: int
    title: str
    company: str | None = None
    location: str | None = None
    snippet: str | None = None
    salary: str | None = None
    type: str | None = None
    source: str | None = None
    link: str
    updated: datetime | None = None

def baca_dari_file(file_path: Path) -> list[JoobleJob]:
    data = json.loads(Path(file_path).read_text(encoding="utf-8"))
    return [JoobleJob(**job) for job in data["jobs"]]

