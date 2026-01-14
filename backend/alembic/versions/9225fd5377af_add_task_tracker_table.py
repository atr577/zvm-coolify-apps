"""add_task_tracker_table

Revision ID: 9225fd5377af
Revises: b735a17c7bad
Create Date: 2026-01-14 17:14:39.412927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9225fd5377af'
down_revision: Union[str, Sequence[str], None] = 'b735a17c7bad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create task_tracker table for idempotent generation."""
    op.create_table(
        'task_tracker',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('external_task_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', name='taskstatus'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_tracker_id', 'task_tracker', ['id'], unique=False)
    op.create_index('ix_task_tracker_video_id', 'task_tracker', ['video_id'], unique=False)
    op.create_index('ix_task_tracker_step_type', 'task_tracker', ['step_type'], unique=False)
    op.create_index('ix_task_tracker_external_task_id', 'task_tracker', ['external_task_id'], unique=False)
    op.create_index('ix_task_tracker_status', 'task_tracker', ['status'], unique=False)


def downgrade() -> None:
    """Drop task_tracker table."""
    op.drop_index('ix_task_tracker_status', table_name='task_tracker')
    op.drop_index('ix_task_tracker_external_task_id', table_name='task_tracker')
    op.drop_index('ix_task_tracker_step_type', table_name='task_tracker')
    op.drop_index('ix_task_tracker_video_id', table_name='task_tracker')
    op.drop_index('ix_task_tracker_id', table_name='task_tracker')
    op.drop_table('task_tracker')
