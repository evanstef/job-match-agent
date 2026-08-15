import logging
from collections import defaultdict

from pydantic import BaseModel
from sqlalchemy.orm import Session

from job_match_api.db.repository import (
    ambil_lowongan_tanpa_isi,
    simpan_isi_lengkap,
    tandai_isi_gagal,
)
from job_match_api.sources.ats import PENGAMBIL, AtsError, ambil_board

logger = logging.getLogger(__name__)


class HasilLengkapi(BaseModel):
    diperiksa: int
    perusahaan: int
    berhasil: int
    gagal: int


def lengkapi(db: Session, batas: int = 100) -> HasilLengkapi:
    """Ambil isi lengkap lowongan dari ATS asalnya, simpan ke kolom isi_lengkap."""
    lowongan = ambil_lowongan_tanpa_isi(db, list(PENGAMBIL), batas)
    if not lowongan:
        return HasilLengkapi(diperiksa=0, perusahaan=0, berhasil=0, gagal=0)

    # dikelompokkan per perusahaan: satu board memuat banyak lowongan sekaligus,
    # jadi 30 lowongan Amartha cukup satu permintaan, bukan tiga puluh
    kelompok: dict[tuple[str, str], list] = defaultdict(list)
    for low in lowongan:
        kelompok[(low.source or "", low.company or "")].append(low)

    terisi: list[tuple[int, str]] = []
    gagal: list[int] = []

    for (source, perusahaan), daftar in kelompok.items():
        try:
            board = ambil_board(source, perusahaan, {low.title for low in daftar})
        except AtsError as e:
            logger.warning("Board %s (%s) tidak bisa diambil: %s", perusahaan, source, e)
            board = {}

        for low in daftar:
            teks = board.get(low.title)
            if teks:
                terisi.append((low.id, teks))
            else:
                gagal.append(low.id)

    simpan_isi_lengkap(db, terisi)
    # yang gagal ikut ditandai supaya tidak dicoba ulang setiap putaran
    tandai_isi_gagal(db, gagal)

    return HasilLengkapi(
        diperiksa=len(lowongan),
        perusahaan=len(kelompok),
        berhasil=len(terisi),
        gagal=len(gagal),
    )
