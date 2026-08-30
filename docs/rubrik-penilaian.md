# Rubrik Penilaian

Acuan tetap yang dipakai untuk menilai satu lowongan terhadap satu CV.

Rubrik ini punya dua fungsi:

1. **Acuan untuk model** — supaya penilaiannya konsisten, tidak berganti kriteria
   setiap kali dipanggil.
2. **Acuan untuk pengujian** — supaya hasilnya bisa dicek manusia, dan bisa
   dibandingkan ketika prompt diubah. Tanpa acuan tetap, perubahan prompt tidak
   bisa dinilai membaik atau memburuk.

## Cara kerja

Syarat **ditarik dari iklan apa adanya**, bukan dari daftar tetap. Iklan yang
minta "punya SIM A" harus bisa masuk. Setiap syarat lalu diberi dua label dan
satu vonis.

```
"Minimal 2 tahun pengalaman Java"
   ├─ dimensi : keterampilan
   ├─ sifat   : lunak
   ├─ vonis   : cocok
   └─ bukti   : "Backend Developer, 2023–sekarang (Java, Spring Boot)"
```

Isinya mengikuti iklan, labelnya seragam — sehingga tetap bisa dibandingkan
antar lowongan dan bisa dihitung.

## Lima dimensi

| # | Dimensi | Sifat | Dinilai terhadap |
|---|---------|-------|------------------|
| 1 | Peran / posisi | lunak | CV |
| 2 | Keterampilan & tools | lunak | CV |
| 3 | Senioritas / lama pengalaman | lunak | CV |
| 4 | Pendidikan & penyaring mati | keras mutlak | CV |
| 5 | Lokasi & penempatan | keras bersyarat | preferensi pengguna |

### Tiga sifat syarat

**Lunak** — masih bisa dijelaskan di surat lamaran atau dinegosiasi.
Contoh: kurang satu tahun pengalaman, belum pernah pakai salah satu tool.

**Keras mutlak** — tidak bisa diubah oleh pelamar, seberapa pun ia mau.
Contoh: IPK minimum 3.0, wajib lulusan jurusan tertentu, batas usia.
Kalau gagal di sini, lamaran ditolak sebelum dibaca orang.

**Keras bersyarat** — bukan soal mampu, tapi soal **mau**. Hanya pengguna yang
tahu jawabannya, jadi tidak boleh diputuskan agent dari isi CV.
Contoh: domisili, bersedia pindah kota, mau bekerja remote.

> Domisili di CV **tidak boleh dipakai** sebagai penyaring. CV sering menuliskan
> kota asal, bukan kota tempat orangnya sekarang bekerja atau bersedia pindah.

## Vonis per syarat

| Vonis | Arti | Syarat |
|-------|------|--------|
| ✅ cocok | terpenuhi | **wajib menyertakan baris CV sebagai bukti** |
| ❌ tidak cocok | tidak terpenuhi | — |
| ❓ tidak kebaca | iklan tidak menyebut, atau CV tidak menyinggung | — |

`tidak kebaca` **bukan kegagalan** — itu jawaban yang benar ketika informasinya
memang tidak ada. Sekitar dua pertiga cuplikan iklan tidak memuat syarat
eksplisit sama sekali, jadi vonis ini justru kasus yang sering terjadi.

Klaim `cocok` tanpa bukti tidak diperbolehkan. Ini aturan yang paling penting di
seluruh rubrik: agent tidak boleh mengaku tahu sesuatu yang tidak ia baca.

## Vonis akhir

| Kondisi | Hasil |
|---------|-------|
| Ada syarat **keras mutlak** yang ❌ | **SKIP** |
| Ada syarat **keras bersyarat** yang ❌ | **PERTIMBANGKAN** + sebutkan alasannya |
| Semua keras aman, mayoritas lunak ✅ | **LAMAR** |
| Selain itu | **PERTIMBANGKAN** |

Keras bersyarat tidak pernah menghasilkan SKIP. Agent tidak berhak menutup pintu
untuk orang yang mungkin **mau** merantau atau mau ditempatkan — tugasnya cukup
menyebut konsekuensinya dengan jelas, misalnya:

> *"Lokasi Surabaya, sementara preferensimu Jakarta dan Tangerang."*

## Yang tidak dinilai

**Gaji.** Field `salary` dari sumber hanya terisi 18 dari 100 lowongan, dan yang
terisi pun tidak bisa dipercaya (ditemukan nilai seperti `"17000000 $ per jam"`).
Menilai dimensi yang datanya jarang dan kotor hanya mengundang karangan. Gaji
tetap **ditampilkan apa adanya** ke pengguna, tapi tidak ikut menentukan vonis.

**Kesediaan / kondisi kerja** (siap lembur, siap shift, siap ditempatkan di klien,
status kontrak). Sempat jadi dimensi ke-6 sampai 23 Agu 2026. Dibuang karena
tidak ada sumber datanya: rubrik ini menjanjikan jawabannya diambil saat
onboarding, tapi form onboarding tidak pernah menanyakannya dan tabel
`preferensi` tidak pernah punya kolomnya. Yang mengisi kekosongan itu akhirnya
model — dan tebakannya salah: "Penuh waktu" dibaca sebagai syarat kesediaan lalu
divonis tidak cocok. Sejak 18 Agu vonisnya dipaksa "tidak kebaca" di kode, jadi
kotaknya berdiri tanpa pernah menggerakkan apa pun; diuji 243 kombinasi vonis,
skor dan vonis akhir sama persis dengan atau tanpa kotak ini.

> Kalau suatu saat dimensi ini dihidupkan lagi, kerjakan dari **form-nya dulu**,
> bukan dari rubriknya. Urutan terbalik itu yang membuatnya mati sejak awal.

## Preferensi pengguna

Dimensi 5 tidak bisa dijawab dari CV, jadi diambil saat onboarding:

```
lokasi             text[]   maksimal 3 kota
bersedia_relokasi  bool
mau_remote         bool
```

Batas 3 kota bukan batas desain, tapi batas kuota: sumber data hanya menerima
satu lokasi per permintaan, jadi 3 kota berarti 3 permintaan setiap putaran.
Pengguna yang memilih "mana saja" cukup dilayani satu permintaan dengan lokasi
`Indonesia` — pilihan paling longgar justru paling murah.

## Catatan penerapan

Rubrik ini hanya hidup sepenuhnya kalau teks iklan lengkap tersedia. Kalau yang
ada baru cuplikan pendek, sebagian besar dimensi akan bervonis `tidak kebaca`,
dan hasilnya harus dilaporkan apa adanya — ditandai bahwa detailnya belum
terbaca, bukan dianggap lolos.
