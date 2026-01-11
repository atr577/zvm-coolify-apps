"""add_published_at_to_video

Revision ID: e974dc718072
Revises: 48a1cb03fafc
Create Date: 2026-01-11 10:57:46.501161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e974dc718072'
down_revision: Union[str, Sequence[str], None] = '48a1cb03fafc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add published_at column to videos table."""
    op.add_column('videos', sa.Column('published_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove published_at column from videos table."""
    op.drop_column('videos', 'published_at')
