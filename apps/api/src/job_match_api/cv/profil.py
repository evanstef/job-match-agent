from typing import Any, Literal

from groq import Groq, GroqError
from pydantic import BaseModel, Field, ValidationError, field_validator

from job_match_api.config import settings

MAKS_SKILL = 15
# kuota Groq gratis dihitung per menit; biarkan SDK mundur-teratur sebelum menyerah
MAKS_PERCOBAAN = 5

INSTRUKSI = """Kamu pembaca CV. Baca teks CV lalu keluarkan JSON dengan bentuk persis ini:

  {
    "posisi": "jabatan yang paling sering/terakhir dikerjakan, contoh: Frontend Developer",
    "level": "junior | menengah | senior",
    "pengalaman_tahun": 2.5,
    "skill": ["React", "TypeScript"]
  }

  Aturan:
  - level: <2 tahun = junior, 2-5 tahun = menengah, >5 tahun = senior
  - pengalaman_tahun: angka, boleh desimal. Hitung dari tanggal kerja, bukan dari klaim di ringkasan
  - skill: maksimal 15, tulis nama teknologinya saja
  - Jangan mengarang. Kalau tidak ada di teks, jangan ditulis

  Balas JSON saja, tanpa penjelasan."""


class ProfilError(Exception):
    """Gagal menyusun profil dari teks CV."""


class ProfilCv(BaseModel):
    posisi: str
    level: Literal["junior", "menengah", "senior"]
    pengalaman_tahun: float = Field(ge=0, le=60)
    skill: list[str]

    @field_validator("skill", mode="before")
    @classmethod
    def _buang_yang_bukan_teks(cls, v: Any) -> Any:
        # satu angka nyasar dari LLM tidak boleh membatalkan seluruh profil
        if isinstance(v, list):
            return [s for s in v if isinstance(s, str) and s.strip()][:MAKS_SKILL]
        return v


def ekstrak_profil(teks: str) -> ProfilCv:
    """Baca teks CV pakai LLM, keluarkan profil terstruktur."""
    if not settings.groq_api_key:
        raise ProfilError("API key Groq tidak ditemukan")

    client = Groq(api_key=settings.groq_api_key, max_retries=MAKS_PERCOBAAN)

    try:
        respons = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": INSTRUKSI},
                {"role": "user", "content": teks},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        isi = respons.choices[0].message.content or ""
    except GroqError as e:
        raise ProfilError(f"Gagal menghubungi Groq: {type(e).__name__}") from e
    except (IndexError, AttributeError) as e:
        raise ProfilError("Groq membalas tanpa isi") from e

    try:
        return ProfilCv.model_validate_json(isi)
    except ValidationError as e:
        raise ProfilError(f"Jawaban LLM tidak sesuai bentuk: {e.error_count()} kesalahan") from e
