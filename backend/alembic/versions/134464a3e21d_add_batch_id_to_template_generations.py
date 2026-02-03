"""add batch_id to template_generations

Revision ID: 134464a3e21d
Revises: 0fa38b1c1b91
Create Date: 2026-02-03 16:54:21.367702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '134464a3e21d'
down_revision: Union[str, Sequence[str], None] = '0fa38b1c1b91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('template_generations', sa.Column('batch_id', sa.String(length=36), nullable=True))
    op.create_index(op.f('ix_template_generations_batch_id'), 'template_generations', ['batch_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_template_generations_batch_id'), table_name='template_generations')
    op.drop_column('template_generations', 'batch_id')
