from job_match_api.brain.saring import JARAK_LEVEL_MAKS, _tingkat_judul, saring_kasar
from job_match_api.cv.profil import ProfilCv
from job_match_api.db.models import Lowongan

PROFIL = ProfilCv(
    posisi="FRONT END WEB DEVELOPER",
    peran=["Frontend Developer"],
    level="menengah",
    pengalaman_tahun=3.0,
    skill=["React"],
)


def _low(id_: int, title: str) -> Lowongan:
    return Lowongan(id=id_, title=title, link="x")


def test_tingkat_judul_none_kalau_judul_tidak_menyebut_level():
    """Mayoritas judul tidak menyebut level — itu bukan alasan membuang."""
    assert _tingkat_judul("Backend Engineer") is None


def test_tingkat_judul_diambil_yang_tertinggi():
    """'Senior Engineering Manager' punya dua penanda; yang menentukan yang tertinggi."""
    assert _tingkat_judul("Senior Engineering Manager") == 3


def test_level_terlalu_jauh_dibuang():
    """Direktur dan magang sama-sama di luar jangkauan pelamar menengah."""
    hasil = saring_kasar(PROFIL, [_low(1, "Project Director"), _low(2, "Backend Engineer")])

    assert [low.id for low in hasil] == [2]


def test_jarak_level_pas_di_batas_ikut_dibuang():
    """Batasnya >= JARAK_LEVEL_MAKS, bukan >. Dikunci supaya tidak bergeser diam-diam."""
    assert JARAK_LEVEL_MAKS == 2
    assert saring_kasar(PROFIL, [_low(1, "Intern Developer")]) == []


def test_sudah_dikirim_dibuang():
    hasil = saring_kasar(PROFIL, [_low(1, "Web Developer"), _low(2, "Web Developer")], frozenset({1}))

    assert [low.id for low in hasil] == [2]


def test_kecocokan_bidang_tidak_diperiksa_lagi():
    """Sengaja: itu tugas jarak vektor di ambil_lowongan_belum_dinilai.

    Aturan kata yang dulu ada di sini meloloskan 10 dari 263 lowongan, dan sembilan
    di antaranya justru peringkat 50-218 dari kedekatan ke CV.
    """
    hasil = saring_kasar(PROFIL, [_low(1, "Marketing Executive"), _low(2, "HR Officer")])

    assert len(hasil) == 2


def test_urutan_masuk_dipertahankan():
    """Yang masuk sudah terurut jarak vektor ke CV. Menyaring tidak boleh mengacaknya —
    urutan itulah yang menentukan siapa yang dinilai duluan dan siapa yang terpotong."""
    masuk = [_low(3, "Web Developer"), _low(1, "Backend Engineer"), _low(2, "Full Stack Developer")]

    hasil = saring_kasar(PROFIL, masuk)

    assert [low.id for low in hasil] == [3, 1, 2]


def test_daftar_kosong_tidak_meledak():
    assert saring_kasar(PROFIL, []) == []
