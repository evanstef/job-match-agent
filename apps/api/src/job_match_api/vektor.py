import logging
from functools import lru_cache

from fastembed import TextEmbedding

from job_match_api.teks import bersihkan

logger = logging.getLogger(__name__)

# multilingual: CV dan lowongan bercampur Indonesia-Inggris dalam satu kalimat.
# 384 dimensi, sama dengan kolom Vector(384) yang sudah ada di cv & lowongan.
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIMENSI = 384

# tokenizer model ini memotong di 128 token — bukan 512 seperti tertulis di
# deskripsinya. Diuji: dua teks yang ekornya beda total menghasilkan vektor
# identik begitu awalannya lewat 128 token. Karena itu yang di-embed adalah
# profil hasil sulingan LLM (58 token), bukan teks mentah CV (1.100 token).
BATAS_TOKEN = 128


class VektorError(Exception):
    """Kesalahan saat mengubah teks jadi vektor."""


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    """Muat sekali, dipakai seterusnya. Panggilan pertama ~1,7 detik."""
    logger.info("Memuat model embedding %s", MODEL)
    return TextEmbedding(model_name=MODEL)


def kalimat_profil(profil: dict) -> str:
    """Susun profil jadi satu kalimat untuk di-embed.
    WAJIB satu-satunya tempat susunan ini ditulis. Kalau pengisian susulan
    menyusunnya sedikit berbeda, vektor lama dan baru tidak lagi sebanding —
    tanpa error, hasil pencocokannya saja yang pelan-pelan melenceng.
    """
    posisi = str(profil.get("posisi") or "").strip()
    level = str(profil.get("level") or "").strip()
    tahun = profil.get("pengalaman_tahun")
    skill = profil.get("skill")
    daftar = ", ".join(str(s).strip() for s in skill) if isinstance(skill, list) else ""

    bagian = [p for p in (posisi, f"level {level}" if level else "") if p]
    if tahun is not None:
        bagian.append(f"pengalaman {tahun} tahun")

    if not bagian and not daftar:
        raise VektorError("Profil tidak punya posisi maupun skill")

    kalimat = ", ".join(bagian)
    if not daftar:
        return f"{kalimat}."
    return f"{kalimat}. Keahlian: {daftar}." if kalimat else f"Keahlian: {daftar}."


def kalimat_lowongan(judul: str, cuplikan: str | None) -> str:
    return bersihkan(f"{judul} {cuplikan or ''}")


def dari_teks(teks: str) -> list[float]:
    """Ubah satu teks jadi 384 angka.

    Sengaja satu per satu, bukan serombongan. Diukur pada 100 lowongan: satu per
    satu 1,1 detik, serombongan 1,5 detik — dan kalau serombongan, satu baris
    bermasalah menjatuhkan seluruh rombongan.
    """
    bersih = teks.strip()
    if not bersih:
        raise VektorError("Teks kosong, tidak ada yang bisa di-embed")

    try:
        hasil = next(iter(_model().embed([bersih])))
    except Exception as e:
        raise VektorError(f"Model embedding gagal: {type(e).__name__}: {e}") from e

    return [float(x) for x in hasil]


def dari_profil(profil: dict) -> list[float]:
    return dari_teks(kalimat_profil(profil))
