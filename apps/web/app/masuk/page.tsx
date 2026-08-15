"use client";

import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { api, minta, pesanError } from "@/lib/api";
import { naik, wadah } from "@/lib/animasi";
import {
  periksaKolom,
  petaError,
  skemaDaftar,
  skemaMasuk,
  skemaSaya,
  skemaToken,
} from "@/lib/skema";

const KOLOM =
  "mt-1.5 w-full rounded-xl border bg-white px-3.5 py-2.5 font-light outline-none transition focus:ring-4 dark:bg-zinc-900";
const NORMAL =
  "border-zinc-200 focus:border-emerald-500 focus:ring-emerald-500/10 dark:border-zinc-800 dark:focus:border-emerald-500";
const SALAH = "border-red-400 focus:border-red-500 focus:ring-red-500/10";

export default function Masuk() {
  const router = useRouter();
  const [daftar, setDaftar] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [salah, setSalah] = useState<Record<string, string>>({});
  const [sibuk, setSibuk] = useState(false);

  function periksa(nama: string, nilai: unknown) {
    const skema = daftar ? skemaDaftar : skemaMasuk;
    setSalah((s) => ({ ...s, [nama]: periksaKolom(skema, nama, nilai) }));
  }

  async function kirim(e: React.FormEvent) {
    e.preventDefault();

    const hasil = (daftar ? skemaDaftar : skemaMasuk).safeParse({ email, password });
    if (!hasil.success) {
      setSalah(petaError(hasil.error));
      return;
    }

    setSalah({});
    setSibuk(true);
    try {
      await minta(skemaToken, () =>
        api.post(daftar ? "/auth/daftar" : "/auth/masuk", hasil.data),
      );
      const saya = await minta(skemaSaya, () => api.get("/auth/saya"));

      toast.success(daftar ? "Akun dibuat" : `Halo lagi, ${saya.email}`);
      router.push(saya.punya_cv ? "/beranda" : "/onboarding");
    } catch (err) {
      toast.error(pesanError(err));
      setSibuk(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-20">
      <motion.div
        variants={wadah}
        initial="sembunyi"
        animate="muncul"
        className="w-full max-w-sm"
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={daftar ? "daftar" : "masuk"}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <h1 className="text-3xl font-semibold tracking-tight">
              {daftar ? "Buat akun" : "Masuk"}
            </h1>
            <p className="mt-2 font-light text-zinc-600 dark:text-zinc-400">
              {daftar
                ? "Cukup email dan password. Tidak ada verifikasi apa pun."
                : "Lanjutkan ke daftar lowonganmu."}
            </p>
          </motion.div>
        </AnimatePresence>

        <motion.form
          variants={naik}
          onSubmit={kirim}
          noValidate
          className="mt-8 space-y-4"
        >
          <div>
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={(e) => periksa("email", e.target.value)}
              className={`${KOLOM} ${salah.email ? SALAH : NORMAL}`}
            />
            <PesanSalah pesan={salah.email} />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete={daftar ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={(e) => periksa("password", e.target.value)}
              className={`${KOLOM} ${salah.password ? SALAH : NORMAL}`}
            />
            <PesanSalah pesan={salah.password} />
            <AnimatePresence>
              {daftar && !salah.password && (
                <motion.p
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-1.5 overflow-hidden text-sm font-light text-zinc-500"
                >
                  Minimal 8 karakter.
                </motion.p>
              )}
            </AnimatePresence>
          </div>

          <motion.button
            type="submit"
            disabled={sibuk}
            whileHover={{ scale: sibuk ? 1 : 1.02 }}
            whileTap={{ scale: sibuk ? 1 : 0.98 }}
            className="w-full rounded-xl bg-zinc-900 px-4 py-3 font-medium text-white shadow-lg shadow-zinc-900/10 transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
          >
            {sibuk ? "Sebentar..." : daftar ? "Buat akun" : "Masuk"}
          </motion.button>
        </motion.form>

        <motion.button
          variants={naik}
          type="button"
          onClick={() => {
            setDaftar(!daftar);
            setSalah({});
          }}
          className="mt-6 text-sm font-light text-zinc-600 underline-offset-4 transition hover:text-zinc-900 hover:underline dark:text-zinc-400 dark:hover:text-zinc-100"
        >
          {daftar ? "Sudah punya akun? Masuk" : "Belum punya akun? Buat baru"}
        </motion.button>
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
