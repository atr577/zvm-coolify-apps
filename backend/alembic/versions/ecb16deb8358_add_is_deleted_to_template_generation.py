"""add is_deleted to template_generation

Revision ID: ecb16deb8358
Revises: f9c38046cf14
Create Date: 2026-01-30 09:55:21.697760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecb16deb8358'
down_revision: Union[str, Sequence[str], None] = 'f9c38046cf14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('template_generations', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('template_generations', 'is_deleted')
