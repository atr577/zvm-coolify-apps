"""add_remix_fields_to_project

Revision ID: a378f74a4c82
Revises: b92b35fae21c
Create Date: 2026-01-10 22:10:09.967073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a378f74a4c82'
down_revision: Union[str, Sequence[str], None] = 'b92b35fae21c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add remix-specific fields to projects table."""
    op.add_column('projects', sa.Column('source_video_ids', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('scenario_template', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('placeholders', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('placeholder_suggestions', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove remix-specific fields from projects table."""
    op.drop_column('projects', 'placeholder_suggestions')
    op.drop_column('projects', 'placeholders')
    op.drop_column('projects', 'scenario_template')
    op.drop_column('projects', 'source_video_ids')
