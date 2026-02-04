"""add_publishing_metadata_to_template_generations

Revision ID: eed2be6a0ed8
Revises: 134464a3e21d
Create Date: 2026-02-03 19:29:14.371705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'eed2be6a0ed8'
down_revision: Union[str, Sequence[str], None] = '134464a3e21d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('template_generations', sa.Column('publishing_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('template_generations', 'publishing_metadata')
