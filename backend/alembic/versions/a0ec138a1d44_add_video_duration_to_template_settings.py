"""add video_duration to template_settings

Revision ID: a0ec138a1d44
Revises: ecb16deb8358
Create Date: 2026-01-30 10:46:28.214978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0ec138a1d44'
down_revision: Union[str, Sequence[str], None] = 'ecb16deb8358'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('template_settings', sa.Column('video_duration', sa.String(length=10), nullable=False, server_default='5'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('template_settings', 'video_duration')
