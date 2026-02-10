"""add scheduled_for to approved_generations

Revision ID: 865ed2397fb4
Revises: 0f5e95565d92
Create Date: 2026-02-10 14:22:24.344814

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '865ed2397fb4'
down_revision: Union[str, Sequence[str], None] = '0f5e95565d92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('approved_generations', sa.Column('scheduled_for', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('approved_generations', 'scheduled_for')
