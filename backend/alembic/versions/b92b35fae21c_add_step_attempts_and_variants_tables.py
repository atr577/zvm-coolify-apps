"""add step_attempts and variants tables

Revision ID: b92b35fae21c
Revises: f8cbf249c97e
Create Date: 2026-01-10 21:27:26.903722

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b92b35fae21c'
down_revision: Union[str, Sequence[str], None] = 'f8cbf249c97e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Note: step_attempts and variants tables already exist in DB

    # Add is_published to videos
    op.add_column('videos', sa.Column('is_published', sa.Boolean(), nullable=True, default=False))
    op.create_index(op.f('ix_videos_is_published'), 'videos', ['is_published'], unique=False)

    # Add selected_variant_id to workflow_steps
    op.add_column('workflow_steps', sa.Column('selected_variant_id', sa.Integer(), nullable=True))
    # Note: SQLite doesn't support adding FK constraints after table creation without batch mode


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('workflow_steps', 'selected_variant_id')
    op.drop_index(op.f('ix_videos_is_published'), table_name='videos')
    op.drop_column('videos', 'is_published')
