import axios, { type AxiosResponse } from "axios";
import type { ZodType } from "zod";

// withCredentials wajib: tanpa ini cookie httpOnly dari backend tidak ikut terkirim,
// dan semua endpoint yang butuh login akan balas 401 tanpa alasan yang jelas
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010",
  withCredentials: true,
});

/** Bentuk error dari backend: { sukses: false, errors: [...] } */
interface BadanError {
  sukses: boolean;
  errors: string[];
}

function badanError(data: unknown): BadanError | null {
  if (typeof data !== "object" || data === null) return null;
  const calon = data as Partial<BadanError>;
  if (!Array.isArray(calon.errors)) return null;
  return { sukses: Boolean(calon.sukses), errors: calon.errors.map(String) };
}

/** Ambil pesan yang layak ditampilkan ke pengguna dari error apa pun. */
export function pesanError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const badan = badanError(e.response?.data);
    if (badan?.errors.length) return badan.errors[0];
    if (!e.response) return "Tidak bisa menghubungi server";
  }
  if (e instanceof Error && e.message) return e.message;
  return "Terjadi kesalahan";
}

/**
 * Panggil backend lalu periksa bentuk balasannya.
 *
 * api.get<T>() hanya menempelkan tipe — TypeScript percaya begitu saja dan
 * tidak ada yang menjaganya saat program jalan. Kalau backend berubah bentuk,
 * kesalahannya baru muncul jauh di dalam komponen sebagai "undefined".
 * Diperiksa di sini supaya ketahuan di tempat datanya masuk.
 */
export async function minta<T>(
  skema: ZodType<T>,
  panggil: () => Promise<AxiosResponse<unknown>>,
): Promise<T> {
  const { data } = await panggil();
  const hasil = skema.safeParse(data);
  if (!hasil.success) {
    throw new Error("Balasan server tidak sesuai bentuk yang diharapkan");
  }
  return hasil.data;
}
