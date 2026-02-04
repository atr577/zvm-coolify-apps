"""drop_old_preferred_time_column

Revision ID: 99bc482a8954
Revises: ed7719853bad
Create Date: 2026-02-04 11:48:44.581297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '99bc482a8954'
down_revision: Union[str, Sequence[str], None] = 'ed7719853bad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop old preferred_time column (replaced by preferred_times JSON)."""
    op.drop_column('publishing_configs', 'preferred_time')


def downgrade() -> None:
    """Re-add preferred_time column."""
    op.add_column('publishing_configs', sa.Column('preferred_time', sa.VARCHAR(length=5), nullable=False, server_default='18:00'))
