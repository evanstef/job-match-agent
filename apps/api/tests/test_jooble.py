from datetime import datetime
from pathlib import Path

from job_match_api.sources.jooble import JoobleJob, baca_dari_file

# dihitung dari lokasi file ini, bukan dari folder tempat pytest dijalankan
SAMPLE = Path(__file__).resolve().parents[3] / "data" / "jooble-sample-developer-jakarta.json"


def test_baca_dari_file_mengembalikan_semua_lowongan():
    hasil = baca_dari_file(SAMPLE)

    assert len(hasil) == 100
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
    """salary hanya terisi 18 dari 100 — field opsional tidak boleh bikin gagal."""
    hasil = baca_dari_file(SAMPLE)

    assert any(job.salary for job in hasil)
    assert any(not job.salary for job in hasil)


def test_tipe_salah_ditolak():
    """Pydantic menolak di pintu masuk, bukan membiarkan lolos ke database."""
    import pytest

    with pytest.raises(ValueError):
        JoobleJob(id="bukan-angka", title="x", link="y")
