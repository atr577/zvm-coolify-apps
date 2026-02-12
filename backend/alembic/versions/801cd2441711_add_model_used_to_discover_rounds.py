"""add_model_used_to_discover_rounds

Revision ID: 801cd2441711
Revises: 943d56a6ce5d
Create Date: 2026-02-12 11:42:27.529834

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '801cd2441711'
down_revision: Union[str, Sequence[str], None] = '943d56a6ce5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('discover_rounds', sa.Column('model_used', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('discover_rounds', 'model_used')
