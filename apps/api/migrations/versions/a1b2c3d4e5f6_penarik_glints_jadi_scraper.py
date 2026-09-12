"""penarik 'glints' jadi 'scraper'

Sumber lowongan sudah bukan Glints saja (Kalibrr, KitaLulus, Dealls, LinkedIn),
jadi namanya menyesatkan. Kolom `penarik` ikut dipakai sebagai separuh kunci
anti-dobel (penarik, id_penarik) — kalau nilainya diganti di kode tanpa
memindahkan baris lama, penarikan berikutnya menganggap semuanya barang baru
lalu menyimpan duplikat.

Revision ID: a1b2c3d4e5f6
Revises: b8f2a1c93de7
"""

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "b8f2a1c93de7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE lowongan SET penarik = 'scraper' WHERE penarik = 'glints'")


def downgrade() -> None:
    op.execute("UPDATE lowongan SET penarik = 'glints' WHERE penarik = 'scraper'")
