import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session

from job_match_api.db.repository import ambil_lowongan_tanpa_vektor, simpan_vektor_lowongan
from job_match_api.vektor import VektorError, dari_teks, kalimat_lowongan

logger = logging.getLogger(__name__)

# ~11 ms per lowongan, jadi 1.000 baris sekitar 11 detik. Dibuat lebih besar dari
# jumlah yang masuk tiap putaran (~500) supaya tumpukan lama ikut terkejar.
BATAS = 1000


class HasilIsiVektor(BaseModel):
    diperiksa: int
    berhasil: int
    gagal: int


def isi_vektor(db: Session, batas: int = BATAS) -> HasilIsiVektor:
    """Isi vektor untuk lowongan yang belum punya.

    Satu-satunya jalan vektor lowongan terisi — baik yang baru ditarik maupun
    yang sudah lama ada. Duplikat tidak pernah sampai ke sini karena tidak
    pernah masuk tabel.
    """
    lowongan = ambil_lowongan_tanpa_vektor(db, batas)
    if not lowongan:
        return HasilIsiVektor(diperiksa=0, berhasil=0, gagal=0)

    terisi: list[tuple[int, list[float]]] = []
    gagal = 0

    for low in lowongan:
        try:
            terisi.append((low.id, dari_teks(kalimat_lowongan(low.title, low.snippet))))
        except VektorError as e:
            # satu baris bermasalah tidak menjatuhkan yang lain
            gagal += 1
            logger.warning("Vektor lowongan %s gagal: %s", low.id, e)

    simpan_vektor_lowongan(db, terisi)
    return HasilIsiVektor(diperiksa=len(lowongan), berhasil=len(terisi), gagal=gagal)
