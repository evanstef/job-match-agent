"use client";

import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { api, minta, pesanError } from "@/lib/api";
import { kartu, naik, wadah } from "@/lib/animasi";
import {
  petaError,
  skemaPreferensi,
  skemaPreferensiKeluar,
  periksaKolom,
  skemaBacaCv,
  skemaSimpanCv,
  type BacaCvOut,
} from "@/lib/skema";

const KOLOM =
  "mt-1.5 w-full rounded-xl border bg-white px-3.5 py-2.5 font-light outline-none transition focus:ring-4 dark:bg-zinc-900";
const NORMAL =
  "border-zinc-200 focus:border-emerald-500 focus:ring-emerald-500/10 dark:border-zinc-800 dark:focus:border-emerald-500";
const SALAH = "border-red-400 focus:border-red-500 focus:ring-red-500/10";

export default function Onboarding() {
  const router = useRouter();
  const [siap, setSiap] = useState(false);
  const [bacaan, setBacaan] = useState<BacaCvOut | null>(null);
  const profil = bacaan?.profil ?? null;
  const [membaca, setMembaca] = useState(false);
  const [sibuk, setSibuk] = useState(false);

  const [kota, setKota] = useState("");
  const [relokasi, setRelokasi] = useState(false);
  const [remote, setRemote] = useState(true);
  const [nomor, setNomor] = useState("");
  const [salah, setSalah] = useState<Record<string, string>>({});

  function periksa(nama: string, nilai: unknown) {
    setSalah((s) => ({ ...s, [nama]: periksaKolom(skemaPreferensi, nama, nilai) }));
  }

  useEffect(() => {
    api
      .get("/auth/saya")
      .then(() => setSiap(true))
      .catch(() => router.replace("/masuk"));
  }, [router]);

  // hanya membaca — belum menyimpan apa pun. Ganti berkas berkali-kali tidak
  // meninggalkan satu baris pun di database; penyimpanan terjadi saat submit.
  async function unggah(e: React.ChangeEvent<HTMLInputElement>) {
    const berkas = e.target.files?.[0];
    if (!berkas) return;

    setMembaca(true);
    const badan = new FormData();
    badan.append("file", berkas);

    try {
      const data = await minta(skemaBacaCv, () => api.post("/cv/baca", badan));
      setBacaan(data);
      toast.success("CV terbaca", {
        description: `${data.profil.posisi} · ${data.profil.skill.length} skill`,
      });
    } catch (err) {
      toast.error(pesanError(err));
    } finally {
      setMembaca(false);
      // input file tidak memicu onChange kalau nilainya sama; tanpa ini, memilih
      // berkas yang sama setelah gagal terlihat seperti aplikasinya menggantung
      e.target.value = "";
    }
  }

  // satu tombol menyimpan dua-duanya. CV disimpan lebih dulu: kalau dia gagal,
  // preferensi tidak ikut tersimpan dan tidak ada yang setengah jadi.
  async function simpanSemua(e: React.FormEvent) {
    e.preventDefault();
    if (!bacaan) return;

    const hasil = skemaPreferensi.safeParse({
      lokasi: kota
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean),
      bersedia_relokasi: relokasi,
      mau_remote: remote,
      whatsapp: nomor,
    });
    if (!hasil.success) {
      setSalah(petaError(hasil.error));
      return;
    }

    setSalah({});
    setSibuk(true);
    try {
      await minta(skemaSimpanCv, () => api.post("/cv/simpan", bacaan));
      await minta(skemaPreferensiKeluar, () => api.post("/preferensi", hasil.data));
      toast.success("Agent siap jalan");
      router.push("/beranda");
    } catch (err) {
      toast.error(pesanError(err));
      setSibuk(false);
    }
  }

  if (!siap) return null;

  return (
    <main className="flex flex-1 justify-center px-6 py-16">
      <motion.div
        variants={wadah}
        initial="sembunyi"
        animate="muncul"
        className="w-full max-w-lg"
      >
        <motion.h1 variants={naik} className="text-3xl font-semibold tracking-tight">
          Siapkan agent
        </motion.h1>
        <motion.p variants={naik} className="mt-2 font-light text-zinc-600 dark:text-zinc-400">
          Dua langkah, sekali saja.
        </motion.p>

        <motion.section variants={naik} className="mt-10">
          <div className="flex items-center gap-2.5">
            <span
              className={`flex h-7 w-7 items-center justify-center rounded-lg text-sm font-semibold transition-colors ${
                profil
                  ? "bg-emerald-500 text-white"
                  : "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
              }`}
            >
              {profil ? "✓" : "1"}
            </span>
            <h2 className="font-medium">Unggah CV</h2>
          </div>
          <p className="mt-1.5 pl-10 text-sm font-light text-zinc-600 dark:text-zinc-400">
            Berkas PDF, maksimal 5 MB. CV hasil pindaian tidak bisa dibaca.
          </p>

          <motion.label
            whileHover={{ scale: membaca ? 1 : 1.01 }}
            whileTap={{ scale: membaca ? 1 : 0.99 }}
            className="mt-4 flex cursor-pointer items-center justify-center rounded-xl border border-dashed border-zinc-300 bg-white/60 px-4 py-10 text-sm font-light text-zinc-600 transition hover:border-emerald-500 hover:bg-emerald-50/40 dark:border-zinc-700 dark:bg-zinc-900/40 dark:text-zinc-400 dark:hover:bg-emerald-950/20"
          >
            <input
              type="file"
              accept="application/pdf"
              className="hidden"
              disabled={membaca}
              onChange={unggah}
            />
            {membaca ? (
              <span className="flex items-center gap-2.5">
                <motion.span
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="h-4 w-4 rounded-full border-2 border-zinc-300 border-t-emerald-500"
                />
                Membaca CV...
              </span>
            ) : profil ? (
              "Ganti berkas"
            ) : (
              "Pilih berkas PDF"
            )}
          </motion.label>

          <AnimatePresence>
            {profil && (
              <motion.div
                variants={kartu}
                initial="sembunyi"
                animate="muncul"
                exit="keluar"
                className="mt-4 rounded-xl border border-zinc-200/70 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900"
              >
                <p className="text-sm font-light text-zinc-500">
                  Yang kami baca dari CV-mu — belum tersimpan
                </p>
                <p className="mt-2 text-lg font-medium">{profil.posisi}</p>
                <p className="text-sm font-light text-zinc-600 dark:text-zinc-400">
                  {profil.level} &middot; {profil.pengalaman_tahun} tahun pengalaman
                </p>
                <div className="mt-3.5 flex flex-wrap gap-1.5">
                  {profil.skill.map((s, i) => (
                    <motion.span
                      key={s}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.03 }}
                      className="rounded-lg bg-zinc-100 px-2.5 py-1 text-sm font-light dark:bg-zinc-800"
                    >
                      {s}
                    </motion.span>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.section>

        <motion.form variants={naik} onSubmit={simpanSemua} noValidate className="mt-10">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-zinc-900 text-sm font-semibold text-white dark:bg-zinc-100 dark:text-zinc-900">
              2
            </span>
            <h2 className="font-medium">Maumu seperti apa</h2>
          </div>

          <div className="mt-4 space-y-4">
            <div>
              <label htmlFor="kota" className="block text-sm font-medium">
                Kota yang kamu terima
              </label>
              <input
                id="kota"
                value={kota}
                onChange={(e) => setKota(e.target.value)}
                onBlur={(e) =>
                  periksa(
                    "lokasi",
                    e.target.value.split(",").map((k) => k.trim()).filter(Boolean),
                  )
                }
                placeholder="Jakarta, Tangerang"
                className={`${KOLOM} ${salah.lokasi ? SALAH : NORMAL}`}
              />
              {salah.lokasi ? (
                <PesanSalah pesan={salah.lokasi} />
              ) : (
                <p className="mt-1.5 text-sm font-light text-zinc-500">
                  Pisahkan dengan koma, maksimal 3 kota.
                </p>
              )}
            </div>

            <div>
              <label htmlFor="nomor" className="block text-sm font-medium">
                Nomor WhatsApp
              </label>
              <input
                id="nomor"
                value={nomor}
                onChange={(e) => setNomor(e.target.value)}
                onBlur={(e) => periksa("whatsapp", e.target.value)}
                placeholder="0812xxxxxxxx"
                className={`${KOLOM} ${salah.whatsapp ? SALAH : NORMAL}`}
              />
              {salah.whatsapp ? (
                <PesanSalah pesan={salah.whatsapp} />
              ) : (
                <p className="mt-1.5 text-sm font-light text-zinc-500">
                  Ke sinilah daftar lowongannya dikirim.
                </p>
              )}
            </div>

            {[
              { nilai: remote, ubah: setRemote, teks: "Mau kerja remote" },
              { nilai: relokasi, ubah: setRelokasi, teks: "Bersedia pindah kota" },
            ].map((pilihan) => (
              <label
                key={pilihan.teks}
                className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-zinc-200/70 bg-white/60 px-3.5 py-2.5 transition hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900/40"
              >
                <input
                  type="checkbox"
                  checked={pilihan.nilai}
                  onChange={(e) => pilihan.ubah(e.target.checked)}
                  className="h-4 w-4 accent-emerald-500"
                />
                <span className="font-light">{pilihan.teks}</span>
              </label>
            ))}
          </div>

          <motion.button
            type="submit"
            disabled={sibuk || !profil}
            whileHover={{ scale: profil && !sibuk ? 1.02 : 1 }}
            whileTap={{ scale: profil && !sibuk ? 0.98 : 1 }}
            className="mt-6 w-full rounded-xl bg-zinc-900 px-4 py-3 font-medium text-white shadow-lg shadow-zinc-900/10 transition-colors hover:bg-zinc-700 disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
          >
            {profil ? (sibuk ? "Menyimpan..." : "Selesai") : "Unggah CV dulu"}
          </motion.button>
        </motion.form>
      </motion.div>
    </main>
  );
}

function PesanSalah({ pesan }: { pesan?: string }) {
  return (
    <AnimatePresence>
      {pesan && (
        <motion.p
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-1.5 overflow-hidden text-sm font-light text-red-600 dark:text-red-400"
        >
          {pesan}
        </motion.p>
      )}
    </AnimatePresence>
  );
}
