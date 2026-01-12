"""add audio_provider to project

Revision ID: cb0cd160dd5d
Revises: b87a65629261
Create Date: 2026-01-12 16:09:07.501251

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb0cd160dd5d'
down_revision: Union[str, Sequence[str], None] = 'b87a65629261'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add audio_provider column to projects table."""
    op.add_column('projects', sa.Column('audio_provider', sa.String(length=20), nullable=True))

    # Set default provider for existing projects with audio enabled
    op.execute("""
        UPDATE projects
        SET audio_provider = 'kling'
        WHERE audio_mode != 'none' AND audio_provider IS NULL
    """)


def downgrade() -> None:
    """Remove audio_provider column from projects table."""
    op.drop_column('projects', 'audio_provider')
