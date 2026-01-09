"""add project_type field

Revision ID: 714b35b21e97
Revises: 2a1b18b51d3c
Create Date: 2026-01-09 20:32:02.679134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '714b35b21e97'
down_revision: Union[str, Sequence[str], None] = '2a1b18b51d3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('projects', sa.Column('project_type', sa.String(length=20), nullable=False, server_default='discover'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('projects', 'project_type')
