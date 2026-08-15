"use client";

import Link from "next/link";
import { motion } from "motion/react";

import { naik, wadah } from "@/lib/animasi";

const LANGKAH = [
  {
    judul: "Unggah CV",
    isi: "Sekali saja. Isinya dibaca otomatis — posisi, level, dan daftar skill.",
  },
  {
    judul: "Sebutkan maumu",
    isi: "Kota yang kamu terima, bersedia pindah atau tidak, mau remote atau tidak.",
  },
  {
    judul: "Tunggu di WhatsApp",
    isi: "Tiga kali sehari — 08.00, 15.00, 21.00. Kalau tidak ada yang cocok, tidak ada yang dikirim.",
  },
];

export default function Halaman() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-20">
      <motion.div
        variants={wadah}
        initial="sembunyi"
        animate="muncul"
        className="w-full max-w-2xl"
      >
        <motion.div variants={naik} className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          <p className="text-sm font-medium tracking-wide text-emerald-600 dark:text-emerald-400">
            Job Match Agent
          </p>
        </motion.div>

        <motion.h1
          variants={naik}
          className="mt-4 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl"
        >
          Berhenti menyisir
          <br />
          <span className="bg-gradient-to-r from-emerald-600 to-teal-500 bg-clip-text text-transparent">
            ratusan lowongan.
          </span>
        </motion.h1>

        <motion.p
          variants={naik}
          className="mt-5 text-lg font-light leading-8 text-zinc-600 dark:text-zinc-400"
        >
          Setiap hari ada ratusan lowongan baru, dan hampir semuanya tidak cocok
          untukmu. Agent ini yang membacanya — kamu cukup menerima daftar
          pendeknya di WhatsApp, lalu melamar sendiri.
        </motion.p>

        <motion.ol variants={wadah} className="mt-12 space-y-3">
          {LANGKAH.map((langkah, i) => (
            <motion.li
              key={langkah.judul}
              variants={naik}
              whileHover={{ x: 4 }}
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
              className="flex gap-4 rounded-xl border border-zinc-200/70 bg-white/70 p-4 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/60"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-sm font-semibold text-white dark:bg-zinc-100 dark:text-zinc-900">
                {i + 1}
              </span>
              <div>
                <p className="font-medium">{langkah.judul}</p>
                <p className="mt-0.5 font-light text-zinc-600 dark:text-zinc-400">
                  {langkah.isi}
                </p>
              </div>
            </motion.li>
          ))}
        </motion.ol>

        <motion.div variants={naik} className="mt-10 flex items-center gap-5">
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            <Link
              href="/masuk"
              className="inline-block rounded-xl bg-zinc-900 px-6 py-3 font-medium text-white shadow-lg shadow-zinc-900/10 transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
            >
              Mulai sekarang
            </Link>
          </motion.div>
          <Link
            href="/masuk"
            className="font-light text-zinc-600 underline-offset-4 transition hover:text-zinc-900 hover:underline dark:text-zinc-400 dark:hover:text-zinc-100"
          >
            Sudah punya akun
          </Link>
        </motion.div>

        <motion.p
          variants={naik}
          className="mt-14 border-t border-zinc-200 pt-6 text-sm font-light leading-6 text-zinc-500 dark:border-zinc-800"
        >
          Agent ini tidak melamarkan pekerjaan untukmu, dan tidak pernah mengaku
          cocok tanpa menunjuk baris di CV-mu. Kalau syarat di iklannya tidak
          terbaca, itu dikatakan apa adanya.
        </motion.p>
      </motion.div>
    </main>
  );
}
