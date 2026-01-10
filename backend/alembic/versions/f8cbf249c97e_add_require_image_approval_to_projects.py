"""add require_image_approval to projects

Revision ID: f8cbf249c97e
Revises: 714b35b21e97
Create Date: 2026-01-09 21:49:07.805681

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8cbf249c97e'
down_revision: Union[str, Sequence[str], None] = '714b35b21e97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('projects', sa.Column('require_image_approval', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('projects', 'require_image_approval')
