from datetime import datetime
from pathlib import Path

from job_match_api.sources.jooble import JoobleJob, baca_dari_file

# fixture kecil yang ikut repo — supaya test tidak bergantung pada data provider
# yang gitignored (dulu baca dari data/, gagal di CI karena file tak ada)
SAMPLE = Path(__file__).resolve().parent / "fixtures" / "jooble-sample.json"


def test_baca_dari_file_mengembalikan_semua_lowongan():
    hasil = baca_dari_file(SAMPLE)

    assert len(hasil) == 3
    assert all(isinstance(job, JoobleJob) for job in hasil)


def test_id_bigint_negatif_tidak_terpotong():
    """id Jooble 19 digit dan bisa negatif — melebihi batas aman angka JavaScript."""
    hasil = baca_dari_file(SAMPLE)

    assert hasil[0].id == -9199603624530844841


def test_updated_dikonversi_jadi_datetime():
    """Jooble mengirim string ISO; Pydantic yang mengubahnya jadi objek waktu."""
    hasil = baca_dari_file(SAMPLE)
    updated = hasil[0].updated

    assert isinstance(updated, datetime)
    assert updated.year == 2026


def test_field_kosong_boleh_none():
    """salary opsional — sebagian terisi, sebagian tidak; tidak boleh bikin gagal."""
    hasil = baca_dari_file(SAMPLE)

    assert any(job.salary for job in hasil)
    assert any(not job.salary for job in hasil)


def test_tipe_salah_ditolak():
    """Pydantic menolak di pintu masuk, bukan membiarkan lolos ke database."""
    import pytest

    with pytest.raises(ValueError):
        JoobleJob(id="bukan-angka", title="x", link="y")
