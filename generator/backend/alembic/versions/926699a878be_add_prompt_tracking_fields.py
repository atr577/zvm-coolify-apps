"""add_prompt_tracking_fields

Revision ID: 926699a878be
Revises: 9bfff1a2948f
Create Date: 2026-01-09 16:17:46.046629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '926699a878be'
down_revision: Union[str, Sequence[str], None] = '9bfff1a2948f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add prompt tracking fields to workflow_steps."""
    op.add_column('workflow_steps', sa.Column('original_prompt', sa.JSON(), nullable=True))
    op.add_column('workflow_steps', sa.Column('custom_prompt', sa.JSON(), nullable=True))
    op.add_column('workflow_steps', sa.Column('prompt_manually_edited', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Remove prompt tracking fields."""
    op.drop_column('workflow_steps', 'prompt_manually_edited')
    op.drop_column('workflow_steps', 'custom_prompt')
    op.drop_column('workflow_steps', 'original_prompt')
