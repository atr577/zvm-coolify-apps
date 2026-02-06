"""add music_mode to template_settings

Revision ID: 0f5e95565d92
Revises: 61e110c3a531
Create Date: 2026-02-06 18:00:54.850058

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0f5e95565d92'
down_revision: Union[str, Sequence[str], None] = '61e110c3a531'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('template_settings', sa.Column('music_mode', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('template_settings', 'music_mode')
