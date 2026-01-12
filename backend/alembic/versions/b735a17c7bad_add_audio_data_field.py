"""add_audio_data_field

Revision ID: b735a17c7bad
Revises: cb0cd160dd5d
Create Date: 2026-01-12 18:48:03.933453

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b735a17c7bad'
down_revision: Union[str, Sequence[str], None] = 'cb0cd160dd5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add audio_data column for ai_music step result."""
    op.add_column('videos', sa.Column('audio_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove audio_data column."""
    op.drop_column('videos', 'audio_data')
