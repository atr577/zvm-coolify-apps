"""add_local_media_paths

Revision ID: a3e98d371ffb
Revises: e974dc718072
Create Date: 2026-01-11 18:02:11.460055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3e98d371ffb'
down_revision: Union[str, Sequence[str], None] = 'e974dc718072'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add local media path columns to videos table."""
    op.add_column('videos', sa.Column('local_image_path', sa.String(length=500), nullable=True))
    op.add_column('videos', sa.Column('local_video_path', sa.String(length=500), nullable=True))
    op.add_column('videos', sa.Column('local_audio_path', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Remove local media path columns from videos table."""
    op.drop_column('videos', 'local_audio_path')
    op.drop_column('videos', 'local_video_path')
    op.drop_column('videos', 'local_image_path')
