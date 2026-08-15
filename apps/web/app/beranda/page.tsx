"use client";

import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { api, minta, pesanError } from "@/lib/api";
import { kartu, naik, wadah } from "@/lib/animasi";
import {
  skemaHasilJalan,
  skemaPreferensiKeluar,
  skemaSaya,
  type HasilJalan,
  type Preferensi,
  type SayaOut,
} from "@/lib/skema";

const WARNA_VONIS: Record<string, string> = {
  LAMAR: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  PERTIMBANGKAN: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  SKIP: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
};

const KARTU =
  "rounded-2xl border border-zinc-200/70 bg-white/80 p-5 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/70";

export default function Beranda() {
  const router = useRouter();
  const [saya, setSaya] = useState<SayaOut | null>(null);
  const [preferensi, setPreferensi] = useState<Preferensi | null>(null);
  const [hasil, setHasil] = useState<HasilJalan | null>(null);
  const [sibuk, setSibuk] = useState(false);

  useEffect(() => {
    Promise.all([
      minta(skemaSaya, () => api.get("/auth/saya")),
      minta(skemaPreferensiKeluar, () => api.get("/preferensi")),
    ])
      .then(([a, b]) => {
        setSaya(a);
        setPreferensi(b);
        if (!a.punya_cv) router.replace("/onboarding");
      })
      .catch(() => router.replace("/masuk"));
  }, [router]);

  async function jalankan() {
    setSibuk(true);
    const menunggu = toast.loading("Menilai lowongan...", {
      description: "Tiap lowongan dijeda 10 detik karena batas kuota.",
    });

    try {
      const data = await minta(skemaHasilJalan, () =>
        api.post("/pencocokan/jalankan", null, { params: { maks_dinilai: 10 } }),
      );
      setHasil(data);

      if (data.terpilih.length) {
        toast.success(`${data.terpilih.length} lowongan dikirim ke WhatsApp`, {
          id: menunggu,
          description: `Dari ${data.kandidat} kandidat yang disaring.`,
        });
      } else {
        toast.info("Tidak ada yang cukup cocok putaran ini", {
          id: menunggu,
          description: "Tidak ada yang dikirim — itu memang perilakunya.",
        });
      }
    } catch (e) {
      toast.error(pesanError(e), { id: menunggu });
    } finally {
      setSibuk(false);
    }
  }

  async function keluar() {
    await api.post("/auth/keluar");
    toast.success("Sampai jumpa");
    router.replace("/masuk");
  }

  if (!saya) return null;

  return (
    <main className="flex flex-1 justify-center px-6 py-14">
      <motion.div
        variants={wadah}
        initial="sembunyi"
        animate="muncul"
        className="w-full max-w-2xl"
      >
        <motion.div variants={naik} className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Agent kamu</h1>
            <p className="mt-1 font-light text-zinc-600 dark:text-zinc-400">
              {saya.email}
            </p>
          </div>
          <button
            type="button"
            onClick={keluar}
            className="text-sm font-light text-zinc-500 underline-offset-4 transition hover:text-zinc-900 hover:underline dark:hover:text-zinc-100"
          >
            Keluar
          </button>
        </motion.div>

        <motion.section variants={naik} className={`mt-8 ${KARTU}`}>
          <h2 className="font-medium">Setelan</h2>
          <dl className="mt-3 space-y-2 text-sm">
            {[
              ["Kota", preferensi?.lokasi.join(", ") || "belum diisi"],
              ["Dikirim ke", preferensi?.whatsapp?.replace("@c.us", "") || "belum diisi"],
              [
                "Cara kerja",
                `${preferensi?.mau_remote ? "mau remote" : "tidak remote"} · ${
                  preferensi?.bersedia_relokasi ? "bersedia pindah" : "tidak pindah"
                }`,
              ],
            ].map(([label, nilai]) => (
              <div key={label} className="flex gap-3">
                <dt className="w-28 shrink-0 font-light text-zinc-500">{label}</dt>
                <dd className="font-light">{nilai}</dd>
              </div>
            ))}
          </dl>
          <a
            href="/onboarding"
            className="mt-4 inline-block text-sm font-light text-zinc-600 underline-offset-4 transition hover:text-zinc-900 hover:underline dark:text-zinc-400 dark:hover:text-zinc-100"
          >
            Ubah setelan
          </a>
        </motion.section>

        <motion.section variants={naik} className={`mt-5 ${KARTU}`}>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <h2 className="font-medium">Jalan otomatis 3&times; sehari</h2>
          </div>
          <p className="mt-1.5 text-sm font-light text-zinc-600 dark:text-zinc-400">
            Jam 08.00, 15.00, dan 21.00 WIB. Kamu bisa memicunya sekarang untuk
            melihat hasilnya.
          </p>

          <motion.button
            type="button"
            onClick={jalankan}
            disabled={sibuk}
            whileHover={{ scale: sibuk ? 1 : 1.02 }}
            whileTap={{ scale: sibuk ? 1 : 0.98 }}
            className="mt-4 flex items-center gap-2.5 rounded-xl bg-zinc-900 px-5 py-2.5 font-medium text-white shadow-lg shadow-zinc-900/10 transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
          >
            {sibuk && (
              <motion.span
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="h-4 w-4 rounded-full border-2 border-zinc-400 border-t-transparent"
              />
            )}
            {sibuk ? "Menilai lowongan..." : "Jalankan sekarang"}
          </motion.button>
        </motion.section>

        <AnimatePresence mode="wait">
          {hasil && (
            <motion.section
              key={hasil.dinilai + "-" + hasil.terpilih.length}
              variants={wadah}
              initial="sembunyi"
              animate="muncul"
              className="mt-8"
            >
              <motion.div variants={naik} className="flex flex-wrap gap-2 text-sm">
                {[
                  ["kandidat", hasil.kandidat],
                  ["dinilai", hasil.dinilai],
                  ["terpilih", hasil.terpilih.length],
                  ...(hasil.gagal ? [["gagal", hasil.gagal] as const] : []),
                ].map(([label, angka]) => (
                  <span
                    key={label}
                    className="rounded-lg bg-white/70 px-2.5 py-1 font-light dark:bg-zinc-900/70"
                  >
                    <span className="font-medium">{angka}</span>{" "}
                    <span className="text-zinc-500">{label}</span>
                  </span>
                ))}
              </motion.div>

              {hasil.terpilih.length === 0 ? (
                <motion.p variants={kartu} className={`mt-4 ${KARTU} font-light text-zinc-600 dark:text-zinc-400`}>
                  Tidak ada yang cukup cocok putaran ini. Tidak ada yang dikirim —
                  itu memang perilakunya, bukan kesalahan.
                </motion.p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {hasil.terpilih.map((low) => (
                    <motion.li
                      key={low.id}
                      variants={kartu}
                      whileHover={{ y: -2 }}
                      className={KARTU}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-medium">{low.title}</p>
                          <p className="text-sm font-light text-zinc-600 dark:text-zinc-400">
                            {low.company ?? "-"}
                          </p>
                        </div>
                        <span
                          className={`shrink-0 rounded-lg px-2.5 py-1 text-xs font-medium ${
                            WARNA_VONIS[low.vonis] ?? WARNA_VONIS.SKIP
                          }`}
                        >
                          {low.vonis} {low.skor}
                        </span>
                      </div>

                      <p className="mt-3 text-sm font-light leading-6 text-zinc-600 dark:text-zinc-400">
                        {low.ringkasan}
                      </p>

                      {!low.detail_terbaca && (
                        <p className="mt-2 text-sm font-light text-amber-700 dark:text-amber-400">
                          Syarat detail di iklannya belum terbaca — cek sendiri di
                          tautannya.
                        </p>
                      )}

                      <a
                        href={low.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-3 inline-flex items-center gap-1 text-sm font-medium underline-offset-4 transition hover:underline"
                      >
                        Buka lowongan <span aria-hidden>&rarr;</span>
                      </a>
                    </motion.li>
                  ))}
                </ul>
              )}
            </motion.section>
          )}
        </AnimatePresence>
      </motion.div>
    </main>
  );
}
