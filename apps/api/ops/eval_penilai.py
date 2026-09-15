"""Ukur penilai terhadap golden set berlabel tangan.

Dipakai sebagai gerbang sebelum mengubah rubrik: ubah SATU hal, ukur lagi,
bandingkan. Tanpa ini perbaikan rubrik cuma tebakan yang terdengar masuk akal.

Jalankan:
    uv run python ops/eval_penilai.py [--ulangan 1] [--hanya 7856,7860]
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from job_match_api.brain import otak
from job_match_api.brain.otak import Lowongan, Preferensi, nilai

AKAR = Path(__file__).resolve().parents[3]
GOLDEN = AKAR / "data" / "golden-set.json"

# Ambang vonis mesin, disalin dari pipeline supaya eval menilai hal yang sama
AMBANG_SKOR = 35

# Patokan label manusia: 8-10 LAMAR, 4-7 PERTIMBANGKAN, 1-3 SKIP
def vonis_manusia(skor: int) -> str:
    if skor >= 8:
        return "LAMAR"
    if skor >= 4:
        return "PERTIMBANGKAN"
    return "SKIP"


def spearman(a: list[float], b: list[float]) -> float:
    """Korelasi peringkat. Tidak pakai scipy — cuma ini yang dibutuhkan."""
    def peringkat(x: list[float]) -> list[float]:
        urut = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        i = 0
        while i < len(urut):
            j = i
            while j + 1 < len(urut) and x[urut[j + 1]] == x[urut[i]]:
                j += 1
            rata = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[urut[k]] = rata
            i = j + 1
        return r

    ra, rb = peringkat(a), peringkat(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    atas = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    bawah = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return atas / bawah if bawah else 0.0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ulangan", type=int, default=None, help="timpa ULANGAN (hemat token)")
    p.add_argument("--hanya", default="", help="daftar id dipisah koma")
    p.add_argument("--cv", default="", help="berkas teks CV; kosong = ambil dari DB")
    p.add_argument("--keluar", default="", help="simpan hasil ke JSON")
    # Groq gratis: 8.000 token/menit, satu panggilan ~4.000. Tanpa jeda, separuh
    # lowongan kena 429 dan hasilnya terbaca seperti kegagalan rubrik — bukan.
    p.add_argument("--jeda", type=int, default=35, help="detik antar lowongan")
    arg = p.parse_args()

    if arg.ulangan:
        otak.ULANGAN = arg.ulangan

    golden = json.loads(GOLDEN.read_text())
    if arg.hanya:
        pilih = {int(x) for x in arg.hanya.split(",")}
        golden = [g for g in golden if g["id"] in pilih]

    cv_teks = Path(arg.cv).read_text() if arg.cv else _cv_dari_db()
    pref = Preferensi(lokasi=["Jakarta", "Tangerang", "Bekasi"], mau_remote=True)

    baris = []
    for urutan, g in enumerate(golden):
        if urutan:
            time.sleep(arg.jeda * max(1, otak.ULANGAN))
        low = Lowongan(
            id=g["id"], title=g["judul"], company=g.get("perusahaan"),
            location=g.get("lokasi"), snippet="", link="",
        )
        try:
            h = nilai(cv_teks, pref, low, g["iklan"])
            baris.append({
                "id": g["id"], "judul": g["judul"],
                "manusia": g["skor_saya"], "mesin": h.skor,
                "vonis_mesin": h.vonis, "vonis_manusia": vonis_manusia(g["skor_saya"]),
            })
            print(f"  {g['id']}  manusia={g['skor_saya']:<3} mesin={h.skor:<3} {h.vonis}")
        except Exception as e:  # noqa: BLE001
            print(f"  {g['id']}  GAGAL: {e}")

    if not baris:
        print("Tidak ada yang berhasil dinilai")
        return 1

    cocok = sum(b["vonis_mesin"] == b["vonis_manusia"] for b in baris)
    rho = spearman([b["manusia"] for b in baris], [b["mesin"] for b in baris])

    print()
    print(f"  vonis cocok : {cocok}/{len(baris)} ({round(100*cocok/len(baris))}%)")
    print(f"  korelasi    : {rho:+.2f}")

    if arg.keluar:
        Path(arg.keluar).write_text(json.dumps(baris, indent=1, ensure_ascii=False))
        print(f"  disimpan    : {arg.keluar}")
    return 0


def _cv_dari_db() -> str:
    from job_match_api.db.models import Cv
    from job_match_api.db.session import SessionLocal

    db = SessionLocal()
    try:
        cv = db.query(Cv).order_by(Cv.id.desc()).first()
        if cv is None:
            raise SystemExit("Tidak ada CV di database — pakai --cv <berkas>")
        return cv.teks_mentah
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
