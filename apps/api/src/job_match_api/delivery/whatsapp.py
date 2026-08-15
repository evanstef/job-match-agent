import re

import httpx

from job_match_api.config import settings

AKHIRAN = "@c.us"
PANJANG_NOMOR = (9, 15)


class KurirError(Exception):
    """Pesan gagal dikirim."""


def normalkan_nomor(nomor: str) -> str:
    """Ubah tulisan nomor apa pun jadi bentuk yang dipahami WhatsApp: 628xxx@c.us."""
    angka = re.sub(r"\D", "", nomor.split("@")[0])

    if angka.startswith("0"):
        angka = "62" + angka[1:]
    elif angka.startswith("8"):
        angka = "62" + angka

    if not (PANJANG_NOMOR[0] <= len(angka) <= PANJANG_NOMOR[1]):
        raise KurirError("Nomor WhatsApp tidak sah")

    return angka + AKHIRAN


def kirim(tujuan: str, teks: str) -> None:
    """Kirim pesan lewat layanan whatsapp-web.js lokal."""
    if not tujuan:
        raise KurirError("Tujuan WhatsApp belum diatur")

    try:
        respons = httpx.post(
            f"{settings.whatsapp_url}/send",
            json={"chatId": tujuan, "message": teks},
            timeout=30,
        )
        respons.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise KurirError(f"Layanan WhatsApp menolak (HTTP {e.response.status_code})") from e
    except httpx.RequestError as e:
        # layanannya jalan terpisah dan bisa mati sendiri — bedakan dari penolakan
        raise KurirError(f"Layanan WhatsApp tidak bisa dihubungi ({type(e).__name__})") from e
