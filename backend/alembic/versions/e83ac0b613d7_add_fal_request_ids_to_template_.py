"""add fal request ids to template generation

Revision ID: e83ac0b613d7
Revises: b73399ab812f
Create Date: 2026-01-29 16:23:34.194750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e83ac0b613d7'
down_revision: Union[str, Sequence[str], None] = 'b73399ab812f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('template_generations', sa.Column('fal_image_request_id', sa.String(length=100), nullable=True))
    op.add_column('template_generations', sa.Column('fal_video_request_id', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('template_generations', 'fal_video_request_id')
    op.drop_column('template_generations', 'fal_image_request_id')
