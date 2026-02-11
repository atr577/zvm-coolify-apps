"""add_track_path_to_audio_library

Revision ID: 943d56a6ce5d
Revises: a7f3c2d1e456
Create Date: 2026-02-11 16:33:13.568318

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '943d56a6ce5d'
down_revision: Union[str, Sequence[str], None] = 'a7f3c2d1e456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('audio_library', sa.Column('track_path', sa.String(length=500), nullable=True))
    op.add_column('audio_library', sa.Column('hook_start_ms', sa.Integer(), nullable=True))
    op.add_column('audio_library', sa.Column('hook_end_ms', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('audio_library', 'hook_end_ms')
    op.drop_column('audio_library', 'hook_start_ms')
    op.drop_column('audio_library', 'track_path')
