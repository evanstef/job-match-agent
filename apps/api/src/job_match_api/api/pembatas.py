"""Pembatas laju sederhana untuk endpoint yang bisa ditebak-tebak dari luar.

Disimpan di memori proses, bukan Redis — cukup karena API jalan satu worker.
⚠️ Kalau nanti workernya lebih dari satu, tiap worker punya hitungan sendiri
dan batas efektifnya jadi berlipat; saat itu pindahkan ke penyimpanan bersama.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request

# Ukurannya dipilih supaya manusia yang lupa password tidak pernah tersandung
# (salah 3-4 kali itu wajar), tapi penebak otomatis langsung tertahan.
BATAS_PERCOBAAN = 7
JENDELA_DETIK = 50

_riwayat: dict[tuple[str, str], list[float]] = defaultdict(list)


def _alamat(request: Request) -> str:
    """IP pemanggil. X-Forwarded-For dipakai kalau ada reverse proxy di depan.

    ⚠️ Header itu gampang dipalsukan kalau API terbuka langsung ke internet.
    Sekarang belum ada proxy, jadi request.client yang dipakai; begitu Caddy
    terpasang, header ini yang benar — dan Caddy menimpanya sendiri.
    """
    maju = request.headers.get("x-forwarded-for")
    if maju:
        return maju.split(",")[0].strip()
    return request.client.host if request.client else "tidak diketahui"


def batasi(request: Request, nama: str) -> None:
    """Naikkan hitungan untuk (IP, nama). Lewat batas -> 429 + Retry-After."""
    kunci = (_alamat(request), nama)
    sekarang = time.monotonic()
    batas_bawah = sekarang - JENDELA_DETIK

    # buang jejak yang sudah keluar jendela, sekalian mencegah dict membengkak
    baru = [t for t in _riwayat[kunci] if t > batas_bawah]

    if len(baru) >= BATAS_PERCOBAAN:
        _riwayat[kunci] = baru
        tunggu = int(baru[0] + JENDELA_DETIK - sekarang) + 1
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak percobaan. Coba lagi sebentar.",
            headers={"Retry-After": str(tunggu)},
        )

    baru.append(sekarang)
    _riwayat[kunci] = baru
