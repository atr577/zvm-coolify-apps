"""add_music_to_template_pipeline

Revision ID: b8e7620999ad
Revises: 99bc482a8954
Create Date: 2026-02-04 17:33:17.151521

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b8e7620999ad'
down_revision: Union[str, Sequence[str], None] = '99bc482a8954'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add music fields to template pipeline."""
    op.add_column('template_settings', sa.Column('music_prompt', sa.Text(), nullable=True))
    op.add_column('template_generations', sa.Column('audio_path', sa.String(length=255), nullable=True))
    op.add_column('template_generations', sa.Column('video_with_audio_path', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove music fields from template pipeline."""
    op.drop_column('template_settings', 'music_prompt')
    op.drop_column('template_generations', 'video_with_audio_path')
    op.drop_column('template_generations', 'audio_path')
