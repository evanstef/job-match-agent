from job_match_api.pipeline import LowonganTerpilih


def _tempat(low: LowonganTerpilih) -> str:
    """Perusahaan dan kota jadi satu baris. Yang kosong tidak menyisakan pemisah."""
    return " · ".join(p for p in (low.company, low.location) if p)


def _satu(nomor: int, low: LowonganTerpilih) -> str:
    baris = [f"{nomor}. {low.title}"]

    if tempat := _tempat(low):
        baris.append(f"   {tempat}")

    baris.append(f"   {low.vonis}")
    baris.append(f"   {low.link}")
    return "\n".join(baris)


def susun_pesan(terpilih: list[LowonganTerpilih]) -> str:
    """Ubah daftar lowongan terpilih jadi teks siap kirim. Tidak tahu kanalnya apa.

    Skor sengaja tidak ikut. Dia alat pengurut di dalam kode, bukan penilaian yang
    layak dibaca orang: lowongan yang sama diukur berkali-kali menghasilkan
    36/76/36/56/56, jadi menampilkan angkanya menjanjikan ketelitian yang tidak ada.
    Ringkasan per dimensi ikut ditanggalkan — yang menentukan mau dilamar atau tidak
    adalah posisi, tempat, dan iklannya sendiri.
    """
    if not terpilih:
        return "Belum ada lowongan yang cocok putaran ini."

    kepala = f"{len(terpilih)} lowongan cocok buat kamu:"
    isi = "\n\n".join(_satu(i, low) for i, low in enumerate(terpilih, start=1))
    return f"{kepala}\n\n{isi}"
