"""merge_t30_t31_heads

Revision ID: 8c1bddae81d8
Revises: 5eb68c693efb, b8e7620999ad
Create Date: 2026-02-05 18:16:38.130291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c1bddae81d8'
down_revision: Union[str, Sequence[str], None] = ('5eb68c693efb', 'b8e7620999ad')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
