"""add_is_paused_to_publishing_config

Revision ID: 0fa38b1c1b91
Revises: f7d2e8c3a1b9
Create Date: 2026-02-03 14:55:47.063897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0fa38b1c1b91'
down_revision: Union[str, Sequence[str], None] = 'f7d2e8c3a1b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_paused field to publishing_configs."""
    op.add_column(
        'publishing_configs',
        sa.Column('is_paused', sa.Boolean(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    """Remove is_paused field from publishing_configs."""
    op.drop_column('publishing_configs', 'is_paused')
