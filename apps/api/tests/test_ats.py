from job_match_api.sources.ats import PENGAMBIL, _kunci_judul, _peta_judul, _slug_kandidat, didukung


def test_slug_mencoba_kata_pertama_saja():
    """Diukur 2026-08-22: 'AYANA Hospitality' -> slug board-nya ternyata 'ayana' (129 lowongan).
    Varian kata-pertama ini menemukan 4 board lagi dari 23 perusahaan yang tadinya buntu."""
    assert "ayana" in _slug_kandidat("AYANA Hospitality")


def test_slug_membuang_awalan_dan_akhiran_perusahaan():
    hasil = _slug_kandidat("PT Link Net Tbk")

    assert "linknet" in hasil
    assert not any(s.startswith("pt") for s in hasil)


def test_slug_memotong_di_pemisah():
    """'Funding Societies | Modalku Group' -> board-nya 'fundingsocieties'."""
    assert "fundingsocieties" in _slug_kandidat("Funding Societies | Modalku Group")
    assert "oliver" in _slug_kandidat("OLIVER Agency (APAC)")


def test_slug_mencoba_nama_utuh_walau_ada_pemisah():
    """Dua-duanya nyata: "Funding Societies | Modalku" board-nya potongan depan, tapi
    "Stockbit | Bibit" board-nya justru utuh (stockbitbibit, 31 lowongan)."""
    hasil = _slug_kandidat("Stockbit | Bibit")

    assert hasil[0] == "stockbitbibit"
    assert "stockbit" in hasil


def test_slug_tidak_mengeluarkan_potongan_terlalu_pendek():
    """Slug 1-2 huruf pasti salah dan cuma membuang satu permintaan."""
    assert all(len(s) > 2 for s in _slug_kandidat("PT AB Indonesia"))


def test_slug_tidak_kembar():
    hasil = _slug_kandidat("Botsync")

    assert len(hasil) == len(set(hasil))


def test_kunci_judul_menyamakan_beda_tipis():
    """Judul Jooble sering beda tanda baca dan kapital dengan nama posting di board."""
    assert _kunci_judul("Full-Stack Developer") == _kunci_judul("Full Stack Developer")
    assert _kunci_judul("Backend Engineer ") == _kunci_judul("backend engineer")


def test_kunci_judul_membuang_awalan_copy_of():
    """Board sering menyisakan duplikat berawalan 'Copy of'."""
    assert _kunci_judul("Copy of Senior Lua Developer") == _kunci_judul("Senior Lua Developer")


def test_kunci_judul_tidak_menyamakan_pekerjaan_berbeda():
    """Sengaja TIDAK fuzzy: salah cocok berarti isi iklan perusahaan lain menempel
    ke lowongan ini tanpa suara."""
    assert _kunci_judul("Backend Engineer") != _kunci_judul("Frontend Engineer")
    assert _kunci_judul("Senior Developer") != _kunci_judul("Developer")
    # dua judul berawalan sama -- menangkap kalau kuncinya dipotong jadi awalan saja
    assert _kunci_judul("Software Engineer") != _kunci_judul("Software Engineering Manager")


def test_peta_judul_memetakan_balik_ke_judul_asli():
    """Pengaya mencari lewat low.title, jadi hasilnya wajib berkunci judul asli."""
    peta = _peta_judul({"Full-Stack Developer"})

    assert peta[_kunci_judul("Full Stack Developer")] == "Full-Stack Developer"


def test_sumber_yang_didukung():
    """Enam ATS. Menambah/mengurangi harus disengaja, bukan efek samping refactor."""
    assert set(PENGAMBIL) == {
        "boards.greenhouse.io",
        "breezy.hr",
        "jobsoid.com",
        "manatal.com",
        "smartrecruiters.com",
        "teamtailor.com",
        "workable.com",
    }
    assert didukung("workable.com")
    assert not didukung("glints.com")
    assert not didukung(None)
