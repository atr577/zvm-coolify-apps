"""add_motion_template_to_project

Revision ID: b87a65629261
Revises: e4f5dd7f611a
Create Date: 2026-01-12 01:55:57.909174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b87a65629261'
down_revision: Union[str, Sequence[str], None] = 'e4f5dd7f611a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add motion_template column to projects table."""
    op.add_column('projects', sa.Column('motion_template', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove motion_template column from projects table."""
    op.drop_column('projects', 'motion_template')
