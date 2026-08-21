# Job Match Agent

Agent yang mengambil lowongan kerja baru secara berkala, mencocokkannya dengan CV
pengguna, lalu mengirim daftar pendek yang layak dilamar ke Telegram.

Prinsip utama: **setiap klaim "cocok" wajib menunjuk baris di CV.** Yang tidak
terbaca tidak boleh diklaim.

## Struktur

```
apps/api/     FastAPI + Pydantic (Python, dikelola uv)
apps/web/     Next.js 16 (App Router, Tailwind)
data/         contoh data mentah untuk pengembangan offline
docs/         catatan desain
```

Modul di dalam `apps/api/src/job_match_api/`:

| Folder      | Isi                                              |
|-------------|--------------------------------------------------|
| `sources/`  | pengambil lowongan (Jooble, dll)                  |
| `brain/`    | mesin penilai CV vs lowongan                      |
| `delivery/` | pengirim notifikasi (Telegram; dibuat bisa ditukar) |
| `db/`       | model & migrasi                                   |
| `api/`      | route HTTP                                        |

## Menjalankan

```bash
make setup    # pasang dependency api + web, sekalian bikin .env
make db       # Postgres + pgvector di port 5433
make api      # http://localhost:8010/health
make web      # http://localhost:3010
```

`make` tanpa argumen menampilkan seluruh perintah yang tersedia.

### Konfigurasi

Semua nilai tinggal di **satu** berkas: `apps/api/.env` (contoh:
`apps/api/.env.example`). Dibaca aplikasi lewat `config.py`, dan oleh docker
compose lewat `--env-file` yang dipatok di `Makefile` — sengaja satu, supaya
tidak ada `.env` kedua yang diam-diam berisi nilai berbeda.

Frontend punya berkas sendiri (`apps/web/.env.local`), isinya cuma
`NEXT_PUBLIC_API_URL`. Rahasia backend sengaja tidak pernah sampai ke sana.

### Kenapa Makefile, bukan pnpm workspace

`apps/api` dan `apps/web` adalah dua project mandiri yang kebetulan tinggal di
satu repo — tidak ada paket JS yang dibagi di antara keduanya, jadi pnpm
workspace tidak diperlukan dan justru bikin bentrok. Masing-masing memakai
toolchain sendiri (`uv` untuk Python, `pnpm` untuk Node), dan `Makefile` jadi
lapisan netral di atas keduanya.

## Port

| Layanan  | Port |
|----------|------|
| API      | 8010 |
| Web      | 3010 |
| Postgres | 5433 |

Dipilih agak jauh dari default supaya tidak bentrok dengan project lain.

## Catatan penting

**Host Jooble wajib `id.jooble.org`.** Memakai `jooble.org` tanpa `id.`
menghasilkan `403 Access is available only for registered users` — terlihat
seperti API key mati padahal key-nya sehat.

```
POST https://id.jooble.org/api/{key}
{ "keywords": "...", "location": "...", "ResultOnPage": "100" }
```

Field `id` pada respons Jooble berupa integer 19 digit (bisa negatif), melebihi
batas aman angka JavaScript. Simpan sebagai `BIGINT` atau string.

`data/jooble-sample-developer-jakarta.json` berisi 100 lowongan asli — cukup
untuk membangun seluruh pipeline tanpa memanggil API lagi. Kuota API terbatas,
jadi kembangkan secara offline dari file ini.
