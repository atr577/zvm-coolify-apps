"""add merged_video_path and reference_video_path

Revision ID: 61e110c3a531
Revises: a1d15a15d360
Create Date: 2026-02-06 17:14:23.682169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '61e110c3a531'
down_revision: Union[str, Sequence[str], None] = 'a1d15a15d360'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('discover_projects', sa.Column('merged_video_path', sa.String(length=500), nullable=True))
    op.add_column('template_settings', sa.Column('reference_video_path', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('template_settings', 'reference_video_path')
    op.drop_column('discover_projects', 'merged_video_path')
