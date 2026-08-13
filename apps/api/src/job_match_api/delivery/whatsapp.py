import httpx

from job_match_api.config import settings


class KurirError(Exception):
    """Pesan gagal dikirim."""


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
