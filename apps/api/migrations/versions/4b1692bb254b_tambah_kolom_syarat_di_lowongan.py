"""tambah kolom syarat di lowongan

Revision ID: 4b1692bb254b
Revises: a1b2c3d4e5f6
Create Date: 2026-09-19 11:38:13.505706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4b1692bb254b'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('lowongan', sa.Column('syarat', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('lowongan', sa.Column('syarat_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('lowongan', 'syarat_at')
    op.drop_column('lowongan', 'syarat')
