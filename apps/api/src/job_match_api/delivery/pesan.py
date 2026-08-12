from job_match_api.pipeline import LowonganTerpilih

TANDA_BELUM_TERBACA = "belum lengkap"


def _satu(nomor: int, low: LowonganTerpilih) -> str:
    baris = [f"{nomor}. {low.title}"]

    if low.company:
        baris.append(f"   {low.company}")

    catatan = "" if low.detail_terbaca else f" · {TANDA_BELUM_TERBACA}"
    baris.append(f"   {low.vonis} ({low.skor}){catatan}")

    if low.ringkasan:
        baris.append(f"   {low.ringkasan}")

    baris.append(f"   {low.link}")
    return "\n".join(baris)


def susun_pesan(terpilih: list[LowonganTerpilih]) -> str:
    """Ubah daftar lowongan terpilih jadi teks siap kirim. Tidak tahu kanalnya apa."""
    if not terpilih:
        return "Belum ada lowongan yang cocok putaran ini."

    kepala = f"{len(terpilih)} lowongan cocok buat kamu:"
    isi = "\n\n".join(_satu(i, low) for i, low in enumerate(terpilih, start=1))

    ekor = ""
    if any(not low.detail_terbaca for low in terpilih):
        ekor = (
            f"\n\n({TANDA_BELUM_TERBACA} = syarat detail di iklan belum terbaca, "
            "cek sendiri di tautannya)"
        )

    return f"{kepala}\n\n{isi}{ekor}"
