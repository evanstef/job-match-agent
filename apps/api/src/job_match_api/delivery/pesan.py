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
    if not terpilih:
        return "Belum ada lowongan yang cocok putaran ini."

    kepala = f"{len(terpilih)} lowongan cocok buat kamu:"
    isi = "\n\n".join(_satu(i, low) for i, low in enumerate(terpilih, start=1))
    return f"{kepala}\n\n{isi}"


def susun_kabar_kosong(kandidat: int, dinilai: int, gagal: int) -> str:
    baris = ["Tidak ada lowongan yang cukup cocok putaran ini."]

    if kandidat:
        baris.append(f"Disaring {kandidat} kandidat, {dinilai} dinilai.")
    else:
        baris.append("Belum ada lowongan baru yang layak dinilai.")

    if gagal:
        baris.append(f"{gagal} gagal dinilai.")

    return "\n".join(baris)
