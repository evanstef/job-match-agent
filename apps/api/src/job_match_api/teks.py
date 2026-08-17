import html
import re

# hanya yang benar-benar tag: "<b>", "</div>". "Usia < 30 tahun" tidak ikut terhapus
TAG = re.compile(r"</?[a-zA-Z][^<>]*>")
SPASI = re.compile(r"\s+")


def bersihkan(teks: str) -> str:
    """Buang entitas lalu tag HTML dari teks sumber.

    Dipakai dua pembaca dengan alasan berbeda: OTAK supaya markup tidak terbaca
    sebagai syarat, embedding supaya "&nbsp;" dan "<b>" tidak memakan jatah token.
    Ditulis sekali supaya keduanya tidak pernah melihat teks yang berbeda.
    """
    # entitas dulu, supaya markup yang ter-encode ikut terbuang di langkah berikutnya
    polos = html.unescape(teks)
    return SPASI.sub(" ", TAG.sub(" ", polos)).strip()
