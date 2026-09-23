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
from job_match_api.brain.otak import ekstrak_syarat, nilai
from job_match_api.cv.profil import ProfilCv
from job_match_api.db.models import Lowongan
from job_match_api.pipeline import AMBANG_SKOR, _preferensi

AKAR = Path(__file__).resolve().parents[3]
GOLDEN = AKAR / "data" / "golden-set.json"
# Syarat hasil ekstrak dibekukan di sini: run berikutnya cuma menguji penilai.
# Hapus berkas ini kalau INSTRUKSI_EKSTRAK berubah.
SYARAT = AKAR / "data" / "golden-syarat.json"

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
    p.add_argument("--keluar", default="", help="simpan hasil ke JSON")
    # CI tak punya DB & data/ — ketiganya datang dari secret yang ditulis ke berkas
    p.add_argument("--golden", default=str(GOLDEN), help="berkas golden set")
    p.add_argument("--syarat", default=str(SYARAT), help="berkas syarat beku")
    p.add_argument("--cv-json", default="", help="CV+profil+preferensi; kosong = dari DB")
    # Groq gratis: 8.000 token/menit, satu panggilan ~4.000. Tanpa jeda, separuh
    # lowongan kena 429 dan hasilnya terbaca seperti kegagalan rubrik — bukan.
    p.add_argument("--jeda", type=int, default=35, help="detik antar lowongan")
    # Gerbang CI. Tanpa flag ini script cuma mengukur, tidak pernah gagal.
    p.add_argument("--min-vonis", type=int, default=None, help="minimal vonis cocok")
    p.add_argument("--min-korelasi", type=float, default=None, help="minimal korelasi")
    p.add_argument("--wajib-kirim", action="store_true", help="semua label LAMAR harus terkirim")
    arg = p.parse_args()

    if arg.ulangan:
        otak.ULANGAN = arg.ulangan

    golden = json.loads(Path(arg.golden).read_text())
    if arg.hanya:
        pilih = {int(x) for x in arg.hanya.split(",")}
        golden = [g for g in golden if g["id"] in pilih]

    # CV, profil, dan preferensi diambil persis seperti pipeline.jalankan
    cv_teks, profil, pref = _cv_dari_berkas(arg.cv_json) if arg.cv_json else _cv_dari_db()
    syarat_berkas = Path(arg.syarat)
    simpanan = json.loads(syarat_berkas.read_text()) if syarat_berkas.exists() else {}

    baris = []
    gagal = 0
    for urutan, g in enumerate(golden):
        if urutan:
            time.sleep(arg.jeda * max(1, otak.ULANGAN))
        low = Lowongan(
            id=g["id"], title=g["judul"], company=g.get("perusahaan"),
            location=g.get("lokasi"), snippet="", link="",
        )
        try:
            # sama dengan pipeline: ekstrak sekali, lalu nilai lewat jalur syarat tersimpan
            if str(g["id"]) not in simpanan:
                simpanan[str(g["id"])] = [s.model_dump() for s in ekstrak_syarat(low, g["iklan"])]
                syarat_berkas.write_text(json.dumps(simpanan, indent=1, ensure_ascii=False))
                time.sleep(arg.jeda)
            low.syarat = simpanan[str(g["id"])]
            h = nilai(cv_teks, pref, low, g["iklan"], profil.peran, profil.pendidikan)
            baris.append({
                "id": g["id"], "judul": g["judul"],
                "manusia": g["skor_saya"], "mesin": h.skor,
                "vonis_mesin": h.vonis, "vonis_manusia": vonis_manusia(g["skor_saya"]),
                "kirim": h.vonis != "SKIP" and h.skor >= AMBANG_SKOR,
            })
            print(f"  {g['id']}  manusia={g['skor_saya']:<3} mesin={h.skor:<3} {h.vonis}")
        except Exception as e:  # noqa: BLE001
            gagal += 1
            print(f"  {g['id']}  GAGAL: {e}")

    if not baris:
        print("Tidak ada yang berhasil dinilai")
        return 2

    cocok = sum(b["vonis_mesin"] == b["vonis_manusia"] for b in baris)
    rho = spearman([b["manusia"] for b in baris], [b["mesin"] for b in baris])

    print()
    print(f"  vonis cocok : {cocok}/{len(baris)} ({round(100*cocok/len(baris))}%)")
    print(f"  korelasi    : {rho:+.2f}")

    if arg.keluar:
        Path(arg.keluar).write_text(json.dumps(baris, indent=1, ensure_ascii=False))
        print(f"  disimpan    : {arg.keluar}")
    return periksa(baris, gagal, cocok, rho, arg)


def periksa(baris: list[dict], gagal: int, cocok: int, rho: float, arg: argparse.Namespace) -> int:
    """0 = lolos, 1 = kualitas turun, 2 = hasil tidak sah (ada yang gagal dinilai)."""
    ada_gerbang = arg.min_vonis is not None or arg.min_korelasi is not None or arg.wajib_kirim
    if not ada_gerbang:
        return 0

    # Lowongan yang gagal (429 dll.) bikin angka turun tanpa rubrik salah — ulangi, jangan vonis
    if gagal:
        print(f"\n  TIDAK SAH  : {gagal} lowongan gagal dinilai, ulangi eval")
        return 2

    salah = []
    if arg.min_vonis is not None and cocok < arg.min_vonis:
        salah.append(f"vonis cocok {cocok} < {arg.min_vonis}")
    if arg.min_korelasi is not None and rho < arg.min_korelasi:
        salah.append(f"korelasi {rho:+.2f} < {arg.min_korelasi:+.2f}")
    if arg.wajib_kirim:
        tertinggal = [b["id"] for b in baris if b["vonis_manusia"] == "LAMAR" and not b["kirim"]]
        if tertinggal:
            salah.append(f"label LAMAR tidak terkirim: {tertinggal}")

    print()
    for s in salah:
        print(f"  GAGAL GERBANG: {s}")
    print("  GERBANG LOLOS" if not salah else "  GERBANG DITOLAK")
    return 1 if salah else 0


def _cv_dari_berkas(berkas: str) -> tuple[str, ProfilCv, otak.Preferensi]:
    """Bentuk sama dengan _cv_dari_db, diekspor dari DB sekali lalu disimpan sebagai secret."""
    d = json.loads(Path(berkas).read_text())
    return d["teks_mentah"], ProfilCv(**d["profil"]), otak.Preferensi(**d["preferensi"])


def _cv_dari_db() -> tuple[str, ProfilCv, otak.Preferensi]:
    from job_match_api.db.models import Cv
    from job_match_api.db.session import SessionLocal

    db = SessionLocal()
    try:
        cv = db.query(Cv).order_by(Cv.id.desc()).first()
        if cv is None or cv.profil is None:
            raise SystemExit("Tidak ada CV berprofil di database")
        return cv.teks_mentah, ProfilCv(**cv.profil), _preferensi(cv.user)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
