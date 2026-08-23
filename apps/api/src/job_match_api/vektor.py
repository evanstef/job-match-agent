import logging
import math
from functools import lru_cache

from fastembed import TextEmbedding

from job_match_api.config import settings
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

# Iklan lengkap dipecah supaya semuanya kebagian dibaca, bukan cuma pembukanya.
# 400 huruf + judul ~ 120 token, masih di bawah BATAS_TOKEN walau teksnya padat.
KEPING_HURUF = 400
# p95 panjang iklan 5.958 huruf = 15 keping; 8 dari 175 iklan melewatinya.
# Ekor iklan biasanya bukan syarat lagi, jadi yang terpotong murah harganya.
MAKS_KEPING = 15


class VektorError(Exception):
    """Kesalahan saat mengubah teks jadi vektor."""


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    """Muat sekali, dipakai seterusnya. Panggilan pertama ~1,7 detik."""
    logger.info("Memuat model embedding %s dari %s", MODEL, settings.model_cache_dir)
    return TextEmbedding(model_name=MODEL, cache_dir=settings.model_cache_dir)


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

    # model ini mengeluarkan vektor sepanjang 2,9-4,1; panjangnya tidak menyimpan
    # makna, cuma ikut terbawa. Disamakan jadi 1 supaya perkalian titik biasa pun
    # memberi jawaban yang sama dengan kosinus — <=> sudah kebal, kode lain belum.
    angka = [float(x) for x in hasil]
    panjang = math.sqrt(sum(x * x for x in angka))
    if panjang == 0:
        raise VektorError("Model mengembalikan vektor nol")

    return [x / panjang for x in angka]


def _keping(teks: str) -> list[str]:
    """Pecah teks jadi potongan <= KEPING_HURUF, patah di sela kata."""
    keping: list[str] = []
    kini = ""
    for kata in teks.split():
        if kini and len(kini) + len(kata) + 1 > KEPING_HURUF:
            keping.append(kini)
            kini = kata
        else:
            kini = f"{kini} {kata}".strip()
    if kini:
        keping.append(kini)
    return keping


def _rata(vektor: list[list[float]]) -> list[float]:
    """Rata-ratakan beberapa vektor jadi satu, panjang tetap 1.

    Rata-rata vektor satuan tidak lagi bersatuan panjang. dari_teks menjamin
    panjang 1 dan kode lain bergantung pada jaminan itu, jadi harus disamakan
    lagi di sini. Membagi dengan jumlah keping tidak perlu — pembagian itu
    hilang lagi waktu dinormalkan.
    """
    jumlah = [sum(v[i] for v in vektor) for i in range(DIMENSI)]
    panjang = math.sqrt(sum(x * x for x in jumlah))
    if panjang == 0:
        raise VektorError("Rata-rata keping menghasilkan vektor nol")
    return [x / panjang for x in jumlah]


def dari_lowongan(judul: str, cuplikan: str | None, iklan: str | None = None) -> list[float]:
    """Vektor satu lowongan. Iklan lengkap dipecah dulu; tanpa itu, cuplikan saja.

    Kenapa dipecah, bukan dikirim utuh: tokenizer berhenti di BATAS_TOKEN, jadi
    iklan 3.000 huruf yang dikirim utuh cuma terbaca ~500 huruf pertamanya —
    diukur, memberi vektor yang sama persis dengan mengirim 500 huruf saja.

    Yang membuat itu fatal: di Glints, ~500 huruf pertama adalah tempelan UI
    ("Persyaratan, Hybrid, Minimal S1"), bukan isi lowongan. Diukur 2026-08-23:
    0 dari 9 lowongan front end lolos pintu 0,60, dan yang judulnya persis
    "Front End Developer" pun terukur 0,752. Setelah dipecah 9 dari 9 lolos,
    dan jarak ke lowongan yang tidak sebidang justru melebar (0,21 -> 0,29).
    """
    teks = (iklan or "").strip()
    if not teks:
        return dari_teks(kalimat_lowongan(judul, cuplikan))

    keping = _keping(teks)
    if len(keping) > MAKS_KEPING:
        logger.info(
            "Iklan %s huruf dipotong: %s dari %s keping dipakai",
            len(teks),
            MAKS_KEPING,
            len(keping),
        )
        keping = keping[:MAKS_KEPING]

    return _rata([dari_teks(kalimat_lowongan(judul, k)) for k in keping])


def dari_profil(profil: dict) -> list[float]:
    return dari_teks(kalimat_profil(profil))
