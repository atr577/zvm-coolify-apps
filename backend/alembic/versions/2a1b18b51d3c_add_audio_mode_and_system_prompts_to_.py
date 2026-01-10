"""add audio_mode and system_prompts to projects

Revision ID: 2a1b18b51d3c
Revises: 926699a878be
Create Date: 2026-01-09 18:58:22.826854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a1b18b51d3c'
down_revision: Union[str, Sequence[str], None] = '926699a878be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add audio_mode with default value
    op.add_column('projects', sa.Column('audio_mode', sa.String(length=20), nullable=False, server_default='auto'))
    # Add system_prompts JSON column
    op.add_column('projects', sa.Column('system_prompts', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('projects', 'system_prompts')
    op.drop_column('projects', 'audio_mode')
