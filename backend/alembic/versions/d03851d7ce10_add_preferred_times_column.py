"""add_preferred_times_column

Revision ID: d03851d7ce10
Revises: 8c1bddae81d8
Create Date: 2026-02-05 21:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd03851d7ce10'
down_revision: Union[str, Sequence[str], None] = '8c1bddae81d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add preferred_times JSON column to publishing_configs."""
    op.add_column('publishing_configs', sa.Column('preferred_times', sa.JSON(), nullable=False, server_default='["18:00"]'))
    op.add_column('publishing_configs', sa.Column('is_paused', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Remove preferred_times column."""
    op.drop_column('publishing_configs', 'is_paused')
    op.drop_column('publishing_configs', 'preferred_times')
