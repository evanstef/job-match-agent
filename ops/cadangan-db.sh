#!/usr/bin/env bash
# Cadangan harian kedua database ke berkas terkompresi, simpan 7 hari terakhir.
# Dipanggil cron. Nilai kredensial dibaca dari .env yang sama dengan compose.
set -uo pipefail

DIR_KERJA="${DIR_KERJA:-$HOME/job-match}"
TUJUAN="${TUJUAN:-$HOME/cadangan-db}"
SIMPAN_HARI="${SIMPAN_HARI:-7}"

cd "$DIR_KERJA" || { echo "FATAL: $DIR_KERJA tidak ada"; exit 1; }
mkdir -p "$TUJUAN"

ambil_env() { grep -E "^$1=" .env | head -1 | cut -d= -f2-; }

STAMP=$(date +%Y%m%d-%H%M)
GAGAL=0

# Ukuran minimum yang masuk akal untuk dump berisi. Dump yang gagal di tengah
# sering menghasilkan berkas kecil yang TERLIHAT seperti cadangan — itu lebih
# berbahaya daripada tidak ada cadangan sama sekali, karena memberi rasa aman palsu.
MIN_BYTE=1000

simpan() {
  local nama="$1" container="$2" user="$3" db="$4"
  local berkas="$TUJUAN/${nama}-${STAMP}.sql.gz"

  if ! docker exec "$container" pg_dump -U "$user" -d "$db" 2>/dev/null | gzip > "$berkas"; then
    echo "GAGAL: pg_dump $nama"
    rm -f "$berkas"
    GAGAL=1
    return
  fi

  local ukuran
  ukuran=$(stat -c %s "$berkas" 2>/dev/null || echo 0)
  if [ "$ukuran" -lt "$MIN_BYTE" ]; then
    echo "GAGAL: $nama cuma ${ukuran} byte — dump tidak sah, dibuang"
    rm -f "$berkas"
    GAGAL=1
    return
  fi

  echo "OK: $nama ${ukuran} byte -> $(basename "$berkas")"
}

simpan "jobmatch" jobmatch-db "$(ambil_env POSTGRES_USER)" "$(ambil_env POSTGRES_DB)"
simpan "scraper"  scraper-db   scaper                       scaper

# Yang lama dibuang SETELAH yang baru berhasil — jangan pernah menghapus cadangan
# lama kalau yang baru gagal, itu cara kehilangan dua-duanya sekaligus.
if [ "$GAGAL" -eq 0 ]; then
  find "$TUJUAN" -name "*.sql.gz" -mtime "+$SIMPAN_HARI" -delete
  echo "Bersih-bersih: sisa $(find "$TUJUAN" -name '*.sql.gz' | wc -l) berkas"
else
  echo "Ada yang gagal — cadangan lama SENGAJA tidak dihapus"
fi

exit "$GAGAL"
