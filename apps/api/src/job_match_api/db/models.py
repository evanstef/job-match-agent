from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from job_match_api.db.base import Base


class Lowongan(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    title: Mapped[str]
    company: Mapped[str | None]
