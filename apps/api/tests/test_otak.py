import itertools

from job_match_api.brain import otak
from job_match_api.brain.otak import (
    BOBOT,
    BUKTI_SEMU,
    JARAK_PERAN_MAKS,
    POTONGAN_KERAS_BERSYARAT,
    SIFAT_DARI_DIMENSI,
    Syarat,
    _ringkasan,
    _skor,
    _vonis_akhir,
    _vonis_peran,
)
from job_match_api.vektor import VektorError

VONIS = ("cocok", "tidak cocok", "tidak kebaca")

# 20 angka yang bisa keluar dari _skor, dihitung tangan dari BOBOT dan POTONGAN.
# Ditulis apa adanya, bukan dihitung ulang dari rumus — kalau rumusnya bergeser,
# tes ini yang menjerit, bukan ikut bergeser diam-diam.
SKOR_MUNGKIN = {1, 7, 11, 15, 16, 19, 24, 27, 31, 32, 36, 39, 40, 44, 51, 52, 56, 64, 76}


def _syarat(**vonis_per_dimensi):
    """Enam kotak lengkap; yang tidak disebut diisi 'tidak kebaca'."""
    return [
        Syarat(
            dimensi=d,
            teks="x",
            vonis=vonis_per_dimensi.get(d, "tidak kebaca"),
            bukti="kutipan CV" if vonis_per_dimensi.get(d) == "cocok" else None,
        )
        for d in SIFAT_DARI_DIMENSI
    ]


def test_skor_hanya_menghasilkan_dua_puluh_angka():
    """Ruang skor tertutup dan kecil. Ambang apa pun harus dipilih dari daftar ini."""
    keluar = set()
    for kombinasi in itertools.product(VONIS, repeat=3):
        peran, keterampilan, senioritas = kombinasi
        for lokasi in ("cocok", "tidak cocok"):
            keluar.add(
                _skor(
                    _syarat(
                        peran=peran,
                        keterampilan=keterampilan,
                        senioritas=senioritas,
                        lokasi=lokasi,
                    )
                )
            )

    assert keluar == SKOR_MUNGKIN


def test_skor_nol_disediakan_khusus_untuk_skip():
    """0 penanda SKIP. Keras bersyarat memotong 25 tapi tidak boleh menyentuh 0."""
    assert _skor(_syarat(pendidikan="tidak cocok")) == 0
    assert _skor(_syarat(peran="tidak cocok", lokasi="tidak cocok")) >= 1


def test_tidak_kebaca_dihargai_lebih_tinggi_dari_tidak_cocok():
    """Konsekuensi BOBOT yang disengaja: lowongan yang belum terbaca menang atas
    yang sudah diperiksa dan ternyata tidak cocok. Dikunci supaya perubahannya sadar."""
    buta = _skor(_syarat())
    diperiksa = _skor(_syarat(peran="cocok", keterampilan="tidak cocok", senioritas="tidak cocok"))

    assert BOBOT["tidak kebaca"] > BOBOT["tidak cocok"]
    assert buta > diperiksa


def test_vonis_akhir_lamar_kalau_mayoritas_lunak_cocok():
    assert _vonis_akhir(_syarat(peran="cocok", keterampilan="cocok")) == "LAMAR"


def test_vonis_akhir_skip_kalau_keras_mutlak_gagal():
    """pendidikan satu-satunya keras mutlak; SKIP tidak bisa diselamatkan urutan."""
    assert _vonis_akhir(_syarat(peran="cocok", keterampilan="cocok", pendidikan="tidak cocok")) == "SKIP"


def test_vonis_akhir_pertimbangkan_kalau_keras_bersyarat_gagal():
    assert _vonis_akhir(_syarat(peran="cocok", keterampilan="cocok", lokasi="tidak cocok")) == "PERTIMBANGKAN"


def test_cocok_tanpa_bukti_diturunkan_jadi_tidak_kebaca():
    """LLM terbukti melanggar aturan ini, jadi ditegakkan di kode bukan di prompt."""
    s = Syarat(dimensi="peran", teks="x", vonis="cocok", bukti="")

    assert s.vonis == "tidak kebaca"


def test_ringkasan_tidak_pernah_bertentangan_dengan_vonis():
    """Ringkasan karangan LLM pernah menulis 'tidak layak' untuk lowongan PERTIMBANGKAN."""
    hasil = _ringkasan(_syarat(peran="cocok", lokasi="cocok", keterampilan="tidak cocok"))

    assert "peran" in hasil.lower()
    assert "layak" not in hasil.lower()
    assert hasil.endswith(".")


def test_ringkasan_menyebut_setiap_dimensi_sekali():
    hasil = _ringkasan(_syarat(peran="cocok", keterampilan="tidak cocok"))

    for dimensi in ("peran", "keterampilan", "senioritas", "pendidikan", "lokasi"):
        assert hasil.lower().count(dimensi) == 1
    assert "kesediaan" not in hasil.lower()


def test_vonis_peran_dipatok_cocok_kalau_dekat(monkeypatch):
    monkeypatch.setattr(otak, "dari_teks", lambda t: [1.0])

    assert _vonis_peran(["Frontend Developer"], "judul") == "cocok"


def test_vonis_peran_diserahkan_llm_kalau_jauh(monkeypatch):
    # dua vektor tegak lurus -> jarak 1,0, jauh di atas ambang
    monkeypatch.setattr(otak, "dari_teks", lambda t: [1.0, 0.0] if t == "judul" else [0.0, 1.0])

    assert _vonis_peran(["Frontend Developer"], "judul") is None


def test_vonis_peran_memakai_peran_terdekat(monkeypatch):
    """Cukup SATU peran yang cocok. Pengalaman orang macam-macam, bukan cuma headline."""
    vektor = {"judul": [1.0, 0.0], "jauh": [0.0, 1.0], "dekat": [1.0, 0.0]}
    monkeypatch.setattr(otak, "dari_teks", lambda t: vektor[t])

    assert _vonis_peran(["jauh", "dekat"], "judul") == "cocok"


def test_vonis_peran_diam_kalau_daftar_peran_kosong():
    """CV lama tersimpan tanpa kolom peran — harus jatuh ke perilaku lama, bukan error."""
    assert _vonis_peran([], "Web Developer") is None


def test_vonis_peran_diam_kalau_embedding_gagal(monkeypatch):
    """Model embedding gagal dimuat tidak boleh mengubah vonis jadi tidak cocok."""
    def meledak(_):
        raise VektorError("model tidak ada")

    monkeypatch.setattr(otak, "dari_teks", meledak)

    assert _vonis_peran(["Frontend Developer"], "Web Developer") is None


def test_vonis_peran_tidak_pernah_memvonis_tidak_cocok(monkeypatch):
    """Kode hanya boleh bilang 'cocok' atau diam. Ini yang membedakan bentuk 1 dari bentuk 2."""
    monkeypatch.setattr(otak, "dari_teks", lambda t: [1.0, 0.0] if t == "judul" else [0.0, 1.0])

    assert _vonis_peran(["apa pun"], "judul") != "tidak cocok"


def test_ambang_peran_masih_seperti_yang_diukur():
    """0,46 diukur atas 29 kandidat yang lolos pintu. Menggesernya harus disengaja."""
    assert JARAK_PERAN_MAKS == 0.46
    assert BUKTI_SEMU == 2
    assert POTONGAN_KERAS_BERSYARAT == 25
