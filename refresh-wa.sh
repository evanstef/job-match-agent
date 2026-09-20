#!/bin/sh
# Refresh sesi WhatsApp bot (Baileys) supaya tak desync ("menunggu pesan ini" di HP).
#
# Kenapa: sesi enkripsi Signal antara bot & perangkat penerima bisa jadi tak sinkron
# saat koneksi Baileys putus-nyambung (kode 428) / reboot / deploy. Obatnya: buang
# HANYA session-*.json (creds.json disimpan -> TAK perlu scan QR ulang), restart bot;
# Baileys membangun sesi baru otomatis saat kiriman berikutnya.
#
# Dipasang di cron VPS, jalan tiap pagi SEBELUM putaran 09:00 WIB, jadi kiriman harian
# selalu memakai sesi segar. Ini menambal gejala; akar (Baileys labil) beres kalau
# pindah ke WhatsApp Cloud API resmi.
set -u

BOT=jobmatch-wa-bot

echo "[$(date -u +%FT%TZ)] refresh-wa: mulai"

# 1) pindahkan HANYA session-*.json ke folder bak; JANGAN sentuh creds.json / pre-key /
#    app-state / sender-key. Sekalian bersihkan bak lebih tua dari 3 hari.
docker exec "$BOT" sh -c '
  cd /app/.baileys_auth 2>/dev/null || exit 0
  n=$(ls session-*.json 2>/dev/null | wc -l)
  if [ "$n" -gt 0 ]; then
    d=bak-$(date +%s)
    mkdir -p "$d" && mv session-*.json "$d"/ && echo "  $n sesi dipindah -> $d"
  else
    echo "  tak ada session-*.json (sudah bersih)"
  fi
  find . -maxdepth 1 -name "bak-*" -type d -mtime +3 -exec rm -rf {} + 2>/dev/null
'

# 2) restart bot -> reconnect pakai creds lama (tanpa scan QR)
docker restart "$BOT" >/dev/null && echo "  $BOT direstart"

# 3) tunggu bot kembali "ready" (maks ~90 detik) biar siap sebelum putaran 09:00
s=x
i=0
while [ "$i" -lt 18 ]; do
  sleep 5
  s=$(docker exec "$BOT" node -e 'fetch("http://localhost:3900/status").then(r=>r.json()).then(j=>console.log(j.status)).catch(()=>console.log("x"))' 2>/dev/null || echo x)
  if [ "$s" = ready ]; then
    echo "  bot ready (~$((i * 5 + 5))s)"
    break
  fi
  i=$((i + 1))
done
[ "$s" = ready ] || echo "  ⚠️ bot BELUM ready setelah ~90s — cek manual"

echo "[$(date -u +%FT%TZ)] refresh-wa: selesai"
