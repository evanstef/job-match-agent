import pytest
from pydantic import ValidationError

from job_match_api.cv.profil import ProfilCv


def _profil(**tambahan):
    dasar = {
        "posisi": "Front End Web Developer",
        "level": "junior",
        "pengalaman_tahun": 1.5,
        "skill": ["React"],
    }
    return ProfilCv(**(dasar | tambahan))


def test_cv_lama_tanpa_kolom_pendidikan_tetap_terbaca():
    """Kolom ini menyusul belakangan; profil yang sudah tersimpan tidak boleh gugur."""
    profil = _profil()

    assert profil.pendidikan == ""
    assert profil.pendidikan_status == ""


@pytest.mark.parametrize(
    "ditulis,jadi",
    [
        ("Sarjana (S1)", "S1"),
        ("S1", "S1"),
        ("D3", "Diploma"),
        ("Diploma (D1 - D4)", "Diploma"),
        ("SMK", "SMA/SMK"),
        ("Magister", "S2"),
    ],
)
def test_jenjang_dipetakan_ke_tangga(ditulis, jadi):
    assert _profil(pendidikan=ditulis).pendidikan == jadi


def test_jenjang_asing_jadi_kosong_bukan_menggugurkan_profil():
    """Satu label karangan LLM tidak boleh bikin unggah CV gagal seluruhnya."""
    assert _profil(pendidikan="Kursus Bahasa").pendidikan == ""


def test_status_dibaca_dari_tulisan_bebas():
    assert _profil(pendidikan="S1", pendidikan_status="masih kuliah").pendidikan_status == "belum lulus"
    assert _profil(pendidikan="S1", pendidikan_status="sudah lulus").pendidikan_status == "lulus"


def test_status_tanpa_jenjang_ikut_dikosongkan():
    """Status sendirian tidak bisa dibandingkan dengan syarat mana pun."""
    assert _profil(pendidikan_status="lulus").pendidikan_status == ""


def test_kolom_lain_tetap_ketat():
    """Kelonggaran hanya untuk pendidikan; level yang ngawur tetap ditolak."""
    with pytest.raises(ValidationError):
        _profil(level="dewa")
