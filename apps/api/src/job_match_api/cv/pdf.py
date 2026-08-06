import io

from pypdf import PdfReader


class PdfError(Exception):
    """File PDF tidak bisa dibaca."""


def ekstrak_teks(data: bytes) -> str:
    """Ambil seluruh teks dari file PDF."""
    try:
        reader = PdfReader(io.BytesIO(data))
        halaman = [h.extract_text() or "" for h in reader.pages]
    except Exception as e:
        raise PdfError(f"gagal membaca PDF: {type(e).__name__}") from e

    teks = "\n".join(halaman).strip()
    if not teks:
        raise PdfError("PDF tidak mengandung teks — kemungkinan hasil scan/gambar")

    return teks
