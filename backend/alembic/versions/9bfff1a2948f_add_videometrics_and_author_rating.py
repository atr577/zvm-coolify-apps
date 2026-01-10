"""Add VideoMetrics and author_rating

Revision ID: 9bfff1a2948f
Revises:
Create Date: 2026-01-09 12:04:05.499267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9bfff1a2948f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add author_rating to videos
    op.add_column('videos', sa.Column('author_rating', sa.Integer(), nullable=True))

    # Create video_metrics table
    op.create_table(
        'video_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('video_id', sa.Integer(), sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('period', sa.String(10), nullable=False),  # 30m, 6h, 24h, 7d
        sa.Column('views', sa.Integer(), default=0),
        sa.Column('likes', sa.Integer(), default=0),
        sa.Column('comments', sa.Integer(), default=0),
        sa.Column('shares', sa.Integer(), default=0),
        sa.Column('engagement_rate', sa.Integer(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('is_manual', sa.Boolean(), default=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('video_metrics')
    op.drop_column('videos', 'author_rating')
