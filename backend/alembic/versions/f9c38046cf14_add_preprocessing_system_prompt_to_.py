"""add preprocessing_system_prompt to template_settings

Revision ID: f9c38046cf14
Revises: e83ac0b613d7
Create Date: 2026-01-30 09:50:33.577336

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9c38046cf14'
down_revision: Union[str, Sequence[str], None] = 'e83ac0b613d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('template_settings', sa.Column('preprocessing_system_prompt', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('template_settings', 'preprocessing_system_prompt')
