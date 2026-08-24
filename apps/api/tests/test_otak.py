import itertools

import pytest

from job_match_api.brain import otak
from job_match_api.brain.otak import (
    BOBOT,
    BUKTI_SEMU,
    JARAK_PERAN_MAKS,
    POTONGAN_KERAS_BERSYARAT,
    SIFAT_DARI_DIMENSI,
    OtakError,
    Preferensi,
    Syarat,
    _JawabanLLM,
    _ringkasan,
    _skor,
    _suara,
    _syarat_pendidikan,
    _vonis_akhir,
    _vonis_pendidikan,
    _vonis_peran,
    nilai,
)
from job_match_api.db.models import Lowongan
from job_match_api.vektor import VektorError

VONIS = ("cocok", "tidak cocok", "tidak kebaca")

# 20 angka yang bisa keluar dari _skor, dihitung tangan dari BOBOT dan POTONGAN.
# Ditulis apa adanya, bukan dihitung ulang dari rumus — kalau rumusnya bergeser,
# tes ini yang menjerit, bukan ikut bergeser diam-diam.
SKOR_MUNGKIN = {1, 7, 11, 15, 16, 19, 24, 27, 31, 32, 36, 39, 40, 44, 51, 52, 56, 64, 76}


def _syarat(**vonis_per_dimensi):
    """Lima kotak lengkap; yang tidak disebut diisi 'tidak kebaca'."""
    return [
        Syarat(
            dimensi=d,
            teks="x",
            vonis=vonis_per_dimensi.get(d, "tidak kebaca"),
            bukti="kutipan CV" if vonis_per_dimensi.get(d) == "cocok" else None,
        )
        for d in SIFAT_DARI_DIMENSI
    ]


def _jawaban(**vonis_per_dimensi):
    """Satu jawaban model utuh, lima kotak."""
    return _JawabanLLM(syarat=_syarat(**vonis_per_dimensi))


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


def _vonis(kotak, dimensi):
    return next(s.vonis for s in kotak if s.dimensi == dimensi)


def test_suara_mengambil_mayoritas_dua_dari_tiga():
    """Kasus nyata 23 Agu: pendidikan berpindah vonis, skor ikut lompat 11 lalu 0."""
    kotak = _suara(
        [
            _jawaban(),
            _jawaban(pendidikan="tidak cocok"),
            _jawaban(pendidikan="tidak cocok"),
        ]
    )

    assert _vonis(kotak, "pendidikan") == "tidak cocok"


def test_suara_tanpa_mayoritas_jadi_tidak_kebaca():
    """1-1-1 tidak boleh diselesaikan dengan 'ambil yang pertama' — itu undian lagi."""
    kotak = _suara(
        [
            _jawaban(senioritas="cocok"),
            _jawaban(senioritas="tidak cocok"),
            _jawaban(),
        ]
    )

    assert _vonis(kotak, "senioritas") == "tidak kebaca"


def test_suara_seri_dua_jawaban_jadi_tidak_kebaca():
    """Satu panggilan boleh gagal; yang tersisa dua dan seri tetap tidak punya mayoritas."""
    kotak = _suara([_jawaban(keterampilan="cocok"), _jawaban(keterampilan="tidak cocok")])

    assert _vonis(kotak, "keterampilan") == "tidak kebaca"


def test_suara_satu_jawaban_dipakai_apa_adanya():
    """Dua panggilan gagal bukan alasan membuang yang berhasil."""
    kotak = _suara([_jawaban(keterampilan="cocok")])

    assert _vonis(kotak, "keterampilan") == "cocok"


def test_suara_menolak_daftar_kosong():
    """Nol jawaban tidak boleh diam-diam jadi lima kotak 'tidak kebaca' — itu skor 40
    untuk lowongan yang tidak pernah dibaca siapa pun."""
    with pytest.raises(OtakError):
        _suara([])


def test_suara_bukti_ikut_jawaban_yang_menang():
    """Kalau bukti diambil dari jawaban yang kalah, kotak 'cocok' membawa bukti
    milik 'tidak cocok'."""
    menang = Syarat(dimensi="keterampilan", teks="React", vonis="cocok", bukti="benar")
    kalah = Syarat(dimensi="keterampilan", teks="React", vonis="tidak cocok", bukti=None)

    kotak = _suara(
        [
            _JawabanLLM(syarat=[kalah]),
            _JawabanLLM(syarat=[menang]),
            _JawabanLLM(syarat=[menang]),
        ]
    )
    keterampilan = next(s for s in kotak if s.dimensi == "keterampilan")

    assert keterampilan.vonis == "cocok"
    assert keterampilan.bukti == "benar"


def test_suara_selalu_lima_kotak_urutan_tetap():
    """_skor membagi dengan jumlah kotak — penyebutnya tidak boleh ikut bergoyang."""
    kotak = _suara([_jawaban(peran="cocok"), _jawaban(), _jawaban(lokasi="cocok")])

    assert [s.dimensi for s in kotak] == list(SIFAT_DARI_DIMENSI)


def _lowongan():
    return Lowongan(title="Front End Developer", location="Jakarta Selatan", link="x")


def _pasang_jalur_palsu(monkeypatch, urutan_balasan):
    """Putus jalur jaringan: Groq, _tanya, dan jedanya. Kembalikan pencatat panggilan."""
    monkeypatch.setattr(otak.settings, "groq_api_key", "kunci-uji")
    monkeypatch.setattr(otak, "Groq", lambda **_: object())
    monkeypatch.setattr(otak.time, "sleep", lambda _: None)

    dipanggil = []

    def palsu(*_args):
        balasan = urutan_balasan[len(dipanggil)]
        dipanggil.append(balasan)
        if isinstance(balasan, OtakError):
            raise balasan
        return balasan

    monkeypatch.setattr(otak, "_tanya", palsu)
    return dipanggil


def test_nilai_menanya_model_tiga_kali(monkeypatch):
    """Satu panggilan tidak cukup: itu keadaan yang bikin skor 11 lalu 0."""
    dipanggil = _pasang_jalur_palsu(monkeypatch, [_jawaban(keterampilan="cocok")] * 3)

    hasil = nilai("cv", Preferensi(lokasi=["Jakarta"]), _lowongan())

    assert len(dipanggil) == otak.ULANGAN == 3
    assert _vonis(hasil.syarat, "keterampilan") == "cocok"


def test_nilai_menimpa_vonis_pendidikan_dari_model(monkeypatch):
    """Model boleh bilang apa saja untuk kotak ini; yang dipakai hitungan kode."""
    _pasang_jalur_palsu(monkeypatch, [_jawaban(pendidikan="tidak cocok")] * 3)
    low = _lowongan()
    low.isi_lengkap = "Persyaratan\nMinimal SMA/SMK"

    hasil = nilai("cv", Preferensi(lokasi=["Jakarta"]), low, low.isi_lengkap, pendidikan="S1")

    assert _vonis(hasil.syarat, "pendidikan") == "cocok"
    assert hasil.vonis != "SKIP"


def test_nilai_bertahan_kalau_satu_panggilan_gagal(monkeypatch):
    """Groq tersendat di panggilan kedua bukan alasan melewatkan lowongannya."""
    _pasang_jalur_palsu(
        monkeypatch,
        [_jawaban(peran="cocok"), OtakError("Groq tersendat"), _jawaban(peran="cocok")],
    )

    hasil = nilai("cv", Preferensi(lokasi=["Jakarta"]), _lowongan())

    assert len(hasil.syarat) == 5
    assert _vonis(hasil.syarat, "peran") == "cocok"


def test_nilai_gagal_kalau_semua_panggilan_gagal(monkeypatch):
    """Nol jawaban tidak boleh jadi lima kotak buta yang skornya 40 dan terkirim."""
    _pasang_jalur_palsu(monkeypatch, [OtakError("mati")] * 3)

    with pytest.raises(OtakError):
        nilai("cv", Preferensi(lokasi=["Jakarta"]), _lowongan())


@pytest.mark.parametrize(
    "iklan,jenjang",
    [
        ("Persyaratan\nMinimal Sarjana (S1)\nPengalaman 1 tahun", "S1"),
        ("Minimal Diploma (D1 - D4)", "Diploma"),
        ("Minimal SMA/SMK", "SMA/SMK"),
        ("Pendidikan terakhir minimal S1 jurusan Informatika", "S1"),
    ],
)
def test_syarat_pendidikan_terbaca_dari_iklan(iklan, jenjang):
    """Chip baku Glints maupun tulisan bebas, dua-duanya lewat jalur kode."""
    assert _syarat_pendidikan(iklan) == jenjang


def test_syarat_pendidikan_kosong_kalau_tidak_disebut():
    """Kosong = tidak kebaca. Kotak keras mutlak tidak boleh menutup pintu karena diam."""
    assert _syarat_pendidikan("Dibutuhkan Front End Developer, pengalaman 2 tahun") == ""
    assert _syarat_pendidikan("") == ""


def test_syarat_pendidikan_tidak_tertipu_angka_pengalaman():
    """'minimal 2 tahun' bukan jenjang — kata kunci saja tidak cukup."""
    assert _syarat_pendidikan("Pengalaman kerja minimal 2 tahun") == ""


def test_syarat_pendidikan_ambil_yang_terendah_kalau_berbeda():
    """Meloloskan yang tidak cocok memboroskan 30 detik; menutup yang cocok tidak bisa ditebus."""
    assert _syarat_pendidikan("Minimal Sarjana (S1)\nPendidikan minimal SMA/SMK boleh") == "SMA/SMK"


def _iklan(syarat):
    low = _lowongan()
    low.isi_lengkap = f"Persyaratan\n{syarat}"
    return low


@pytest.mark.parametrize(
    "jenjang_cv,minta,vonis",
    [
        ("S1", "Minimal Sarjana (S1)", "cocok"),
        ("S1", "Minimal SMA/SMK", "cocok"),
        ("S1", "Minimal Diploma (D1 - D4)", "cocok"),
        ("SMA/SMK", "Minimal Sarjana (S1)", "tidak cocok"),
        ("Diploma", "Minimal Sarjana (S1)", "tidak cocok"),
        ("S2", "Minimal Sarjana (S1)", "cocok"),
    ],
)
def test_vonis_pendidikan_membandingkan_peringkat(jenjang_cv, minta, vonis):
    low = _iklan(minta)

    assert _vonis_pendidikan(jenjang_cv, low, low.isi_lengkap) == vonis


def test_vonis_pendidikan_belum_lulus_tetap_memenuhi():
    """Keputusan Evan 24 Agu: sedang menempuh S1 = memenuhi 'Minimal S1'.

    Dipatok di sini supaya tidak bergeser diam-diam — `pendidikan_status` sengaja
    tidak ikut menghitung, jadi satu-satunya yang menjaga aturan ini adalah test.
    """
    low = _iklan("Minimal Sarjana (S1)")

    assert _vonis_pendidikan("S1", low, low.isi_lengkap) == "cocok"


def test_vonis_pendidikan_tidak_kebaca_kalau_salah_satu_sisi_kosong():
    """Keras mutlak tidak boleh menutup pintu gara-gara tidak tahu."""
    tanpa_syarat = _iklan("Pengalaman minimal 2 tahun")

    assert _vonis_pendidikan("S1", tanpa_syarat, tanpa_syarat.isi_lengkap) == "tidak kebaca"

    minta_s1 = _iklan("Minimal Sarjana (S1)")

    assert _vonis_pendidikan("", minta_s1, minta_s1.isi_lengkap) == "tidak kebaca"


def test_vonis_pendidikan_jatuh_ke_cuplikan_kalau_iklan_kosong():
    """Lowongan tanpa isi lengkap masih punya snippet — jangan dibiarkan buta."""
    low = _lowongan()
    low.snippet = "Dicari Front End Developer, minimal SMA/SMK"

    assert _vonis_pendidikan("S1", low, None) == "cocok"
