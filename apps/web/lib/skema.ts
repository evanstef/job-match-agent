import { z } from "zod";

/* ── Masukan dari pengguna ─────────────────────────────────────────────
   Diperiksa sebelum dikirim, supaya salahnya ketahuan tanpa menunggu
   perjalanan ke server. Backend tetap memeriksa ulang — ini kenyamanan,
   bukan pengaman.                                                        */

export const skemaMasuk = z.object({
  email: z.email("Format email tidak benar"),
  password: z.string().min(1, "Password wajib diisi"),
});

export const skemaDaftar = z.object({
  email: z.email("Format email tidak benar"),
  password: z
    .string()
    .min(8, "Password minimal 8 karakter")
    // bcrypt hanya membaca 72 byte pertama, sisanya diabaikan diam-diam
    .max(72, "Password maksimal 72 karakter"),
});

export const skemaPreferensi = z.object({
  lokasi: z.array(z.string()).max(3, "Maksimal 3 kota"),
  whatsapp: z
    .string()
    .trim()
    .min(1, "Nomor WhatsApp wajib diisi")
    .refine((n) => {
      const angka = n.replace(/\D/g, "");
      return angka.length >= 9 && angka.length <= 15;
    }, "Nomor WhatsApp tidak sah"),
  bersedia_relokasi: z.boolean(),
  mau_remote: z.boolean(),
});

/* ── Balasan dari backend ──────────────────────────────────────────────
   Diperiksa juga. Tanpa ini, api.get<T>() cuma janji yang dipercaya
   TypeScript saat compile, dan tidak ada yang menjaganya saat jalan.     */

export const skemaToken = z.object({ token: z.string() });

export const skemaSaya = z.object({
  id: z.number(),
  email: z.string(),
  punya_cv: z.boolean(),
  punya_preferensi: z.boolean(),
});

export const skemaProfilCv = z.object({
  posisi: z.string(),
  level: z.enum(["junior", "menengah", "senior"]),
  pengalaman_tahun: z.number(),
  skill: z.array(z.string()),
});

export const skemaUploadCv = z.object({
  id_cv: z.number(),
  panjang_teks: z.number(),
  profil: skemaProfilCv.nullable(),
});

export const skemaPreferensiKeluar = z.object({
  lokasi: z.array(z.string()),
  bersedia_relokasi: z.boolean(),
  mau_remote: z.boolean(),
  whatsapp: z.string().nullable(),
});

export const skemaLowonganTerpilih = z.object({
  id: z.number(),
  title: z.string(),
  company: z.string().nullable(),
  link: z.string(),
  skor: z.number(),
  vonis: z.enum(["LAMAR", "PERTIMBANGKAN", "SKIP"]),
  ringkasan: z.string(),
  detail_terbaca: z.boolean(),
});

export const skemaHasilJalan = z.object({
  kandidat: z.number(),
  dinilai: z.number(),
  gagal: z.number(),
  terpilih: z.array(skemaLowonganTerpilih),
});

export type SayaOut = z.infer<typeof skemaSaya>;
export type ProfilCv = z.infer<typeof skemaProfilCv>;
export type UploadCvOut = z.infer<typeof skemaUploadCv>;
export type Preferensi = z.infer<typeof skemaPreferensiKeluar>;
export type LowonganTerpilih = z.infer<typeof skemaLowonganTerpilih>;
export type HasilJalan = z.infer<typeof skemaHasilJalan>;

/** Ubah error Zod jadi peta { nama_kolom: pesan } untuk ditempel di form. */
export function petaError(error: z.ZodError): Record<string, string> {
  const peta: Record<string, string> = {};
  for (const masalah of error.issues) {
    const kolom = String(masalah.path[0] ?? "");
    if (kolom && !peta[kolom]) peta[kolom] = masalah.message;
  }
  return peta;
}

/** Periksa satu kolom saja — dipakai saat pengguna pindah dari kolomnya. */
export function periksaKolom(
  skema: { shape: Record<string, z.ZodType> },
  nama: string,
  nilai: unknown,
): string {
  const kolom = skema.shape[nama];
  if (!kolom) return "";
  const hasil = kolom.safeParse(nilai);
  return hasil.success ? "" : hasil.error.issues[0].message;
}
