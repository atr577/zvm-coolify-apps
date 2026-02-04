"""add_variant_generation_prompt

Revision ID: ed7719853bad
Revises: eed2be6a0ed8
Create Date: 2026-02-04 10:39:30.160244

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ed7719853bad'
down_revision: Union[str, Sequence[str], None] = 'eed2be6a0ed8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('template_settings', sa.Column('variant_generation_prompt', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('template_settings', 'variant_generation_prompt')
