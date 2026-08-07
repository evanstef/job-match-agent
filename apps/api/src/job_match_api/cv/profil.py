from groq import APIError, Groq
from pydantic import BaseModel, ValidationError

from job_match_api.config import settings

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
    level: str
    pengalaman_tahun: float
    skill: list[str]


def ekstrak_profil(teks: str) -> ProfilCv:
    """Baca teks CV pakai LLM, keluarkan profil terstruktur."""
    if not settings.groq_api_key:
        raise ProfilError("API key Groq tidak ditemukan")

    client = Groq(api_key=settings.groq_api_key)

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
    except APIError as e:
        raise ProfilError(f"Gagal menghubungi Groq: {type(e).__name__}") from e

    isi = respons.choices[0].message.content or ""

    try:
        return ProfilCv.model_validate_json(isi)
    except ValidationError as e:
        raise ProfilError(f"Jawaban LLM tidak sesuai bentuk: {e.error_count()} kesalahan") from e
