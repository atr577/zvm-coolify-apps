"""add rating fields to template_generation

Revision ID: ce79d43115d7
Revises: a0ec138a1d44
Create Date: 2026-01-30 11:20:08.776011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce79d43115d7'
down_revision: Union[str, Sequence[str], None] = 'a0ec138a1d44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add rating fields to template_generations."""
    op.add_column('template_generations', sa.Column('image_rating', sa.Integer(), nullable=True))
    op.add_column('template_generations', sa.Column('image_comment', sa.Text(), nullable=True))
    op.add_column('template_generations', sa.Column('video_rating', sa.Integer(), nullable=True))
    op.add_column('template_generations', sa.Column('video_comment', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove rating fields from template_generations."""
    op.drop_column('template_generations', 'video_comment')
    op.drop_column('template_generations', 'video_rating')
    op.drop_column('template_generations', 'image_comment')
    op.drop_column('template_generations', 'image_rating')
