"""remove_preprocessing_system_prompt

Revision ID: 746e532489d0
Revises: ce79d43115d7
Create Date: 2026-01-30 14:23:19.661465

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '746e532489d0'
down_revision: Union[str, Sequence[str], None] = 'ce79d43115d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove preprocessing_system_prompt column - not needed, all instructions are in preprocessing_prompt."""
    op.drop_column('template_settings', 'preprocessing_system_prompt')


def downgrade() -> None:
    """Restore preprocessing_system_prompt column."""
    op.add_column('template_settings', sa.Column('preprocessing_system_prompt', sa.TEXT(), nullable=True))
