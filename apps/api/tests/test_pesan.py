from job_match_api.delivery.pesan import susun_kabar_kosong, susun_pesan
from job_match_api.pipeline import LowonganTerpilih


def _low(id_: int = 1, title: str = "Front-end Developer") -> LowonganTerpilih:
    return LowonganTerpilih(
        id=id_,
        title=title,
        company="PT Contoh",
        location="Jakarta",
        link="https://contoh/lowongan",
        skor=60,
        vonis="LAMAR",
        ringkasan="",
        detail_terbaca=True,
    )


def test_susun_pesan_tanpa_gagal_tidak_menyebut_gagal():
    """Putaran mulus tidak boleh memunculkan peringatan yang membingungkan."""
    pesan = susun_pesan([_low()])
    assert "gagal" not in pesan
    assert "1 lowongan cocok" in pesan


def test_susun_pesan_menyebut_yang_gagal_dinilai():
    """Lowongan yang gagal dibuang senyap — pesan harus menyuarakannya."""
    pesan = susun_pesan([_low()], gagal=2)
    assert "2 lowongan gagal dinilai" in pesan


def test_susun_pesan_gagal_nol_diam():
    """gagal=0 sama saja dengan tidak ada yang gagal."""
    assert "gagal" not in susun_pesan([_low()], gagal=0)


def test_kabar_kosong_tetap_menyebut_gagal():
    """Jalur nihil sudah melaporkan gagal; jangan sampai regres."""
    assert "3 gagal dinilai" in susun_kabar_kosong(kandidat=5, dinilai=2, gagal=3)
