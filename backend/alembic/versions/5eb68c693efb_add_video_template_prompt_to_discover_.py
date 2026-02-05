"""add video_template_prompt to discover_extractions

Revision ID: 5eb68c693efb
Revises: 4b0c1b99979d
Create Date: 2026-02-05 13:38:50.698305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5eb68c693efb'
down_revision: Union[str, Sequence[str], None] = '4b0c1b99979d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('discover_extractions', sa.Column('video_template_prompt', sa.Text(), nullable=True))
    op.add_column('discover_extractions', sa.Column('edited_video_template_prompt', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('discover_extractions', 'edited_video_template_prompt')
    op.drop_column('discover_extractions', 'video_template_prompt')
