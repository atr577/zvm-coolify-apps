"""T44: add latest metrics period

Revision ID: a7f3c2d1e456
Revises: c245dcc9af17
Create Date: 2026-02-10 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a7f3c2d1e456'
down_revision: Union[str, Sequence[str], None] = 'c245dcc9af17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'latest' value to metricsperiod enum in PostgreSQL
    op.execute("ALTER TYPE metricsperiod ADD VALUE IF NOT EXISTS 'latest'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly.
    # This would require recreating the enum type, which is complex and risky.
    # In practice, leaving the unused value is safe.
    pass
