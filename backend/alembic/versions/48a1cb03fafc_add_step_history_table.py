"""add_step_history_table

Revision ID: 48a1cb03fafc
Revises: a378f74a4c82
Create Date: 2026-01-10 23:39:35.359256

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48a1cb03fafc'
down_revision: Union[str, Sequence[str], None] = 'a378f74a4c82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create step_history table."""
    op.create_table(
        'step_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(50), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('is_selected', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_step_history_id', 'step_history', ['id'], unique=False)
    op.create_index('ix_step_history_video_id', 'step_history', ['video_id'], unique=False)
    op.create_index('ix_step_history_step_type', 'step_history', ['step_type'], unique=False)


def downgrade() -> None:
    """Drop step_history table."""
    op.drop_index('ix_step_history_step_type', table_name='step_history')
    op.drop_index('ix_step_history_video_id', table_name='step_history')
    op.drop_index('ix_step_history_id', table_name='step_history')
    op.drop_table('step_history')
