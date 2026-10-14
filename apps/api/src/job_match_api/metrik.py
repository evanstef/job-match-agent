"""Angka kerja agent untuk Prometheus. Diambil Grafana Alloy dari port terpisah."""

import logging
from threading import Thread
from typing import Literal
from wsgiref.simple_server import WSGIServer

from groq.types.chat import ChatCompletion
from prometheus_client import Counter, Gauge, disable_created_metrics, start_http_server

logger = logging.getLogger(__name__)

# tanpa ini tiap counter membawa seri *_created juga — jatah seri Grafana terbuang dua kali
disable_created_metrics()

LOWONGAN_DITARIK = Counter("jobmatch_lowongan_ditarik", "Lowongan baru yang masuk dari scraper")
PENILAIAN = Counter("jobmatch_penilaian", "Lowongan yang dinilai, per hasil", ["hasil"])
GROQ_TOKEN = Counter("jobmatch_groq_token", "Token Groq terpakai (jatah gratis 200.000/hari)")
PESAN = Counter("jobmatch_pesan", "Pesan WhatsApp ke user, per jenis & hasil", ["jenis", "hasil"])
PESAN_TERAKHIR = Gauge(
    "jobmatch_pesan_terkirim_terakhir_timestamp_seconds",
    "Kapan pesan terakhir berhasil terkirim (unix detik)",
)

# didaftarkan dari awal supaya seri "gagal" sudah ada bernilai 0 sebelum gagal pertama
for _hasil in ("berhasil", "gagal"):
    PENILAIAN.labels(hasil=_hasil)
for _jenis in ("lowongan", "kabar_kosong"):
    for _hasil in ("terkirim", "gagal"):
        PESAN.labels(jenis=_jenis, hasil=_hasil)

_server: tuple[WSGIServer, Thread] | None = None


def catat_token(respons: ChatCompletion) -> None:
    """Tambahkan token satu panggilan Groq ke hitungan."""
    if respons.usage is not None:
        GROQ_TOKEN.inc(respons.usage.total_tokens)


def catat_pesan(jenis: Literal["lowongan", "kabar_kosong"], terkirim: bool) -> None:
    PESAN.labels(jenis=jenis, hasil="terkirim" if terkirim else "gagal").inc()
    if terkirim:
        PESAN_TERAKHIR.set_to_current_time()


def nyalakan(port: int) -> None:
    """Buka /metrics di port sendiri, terpisah dari 8010 yang diteruskan Caddy ke publik."""
    global _server
    if port == 0:
        logger.info("Server metrik dimatikan (METRIK_PORT=0)")
        return
    _server = start_http_server(port)
    logger.info("Server metrik hidup di port %s", port)


def matikan() -> None:
    global _server
    if _server is not None:
        _server[0].shutdown()
        _server[0].server_close()
        _server = None
