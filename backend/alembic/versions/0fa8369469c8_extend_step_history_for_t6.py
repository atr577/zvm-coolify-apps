"""extend_step_history_for_t6

Revision ID: 0fa8369469c8
Revises: a3e98d371ffb
Create Date: 2026-01-11 22:14:24.397313

T6.1: Extend StepHistory with status tracking, metrics, and lineage fields.

Note: SQLite doesn't enforce FK constraints by default, and we're dropping all data anyway.
The FK relationship is defined in the SQLAlchemy model.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fa8369469c8'
down_revision: Union[str, Sequence[str], None] = 'a3e98d371ffb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new fields to step_history for T6 workflow consolidation."""
    # Status tracking
    op.add_column('step_history', sa.Column('status', sa.String(length=20), nullable=True))
    op.add_column('step_history', sa.Column('error_message', sa.Text(), nullable=True))

    # Metrics
    op.add_column('step_history', sa.Column('generation_time_seconds', sa.Float(), nullable=True))

    # Lineage for regenerate with feedback (no FK constraint for SQLite compatibility)
    op.add_column('step_history', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.add_column('step_history', sa.Column('feedback', sa.Text(), nullable=True))

    # Set default for existing rows
    op.execute("UPDATE step_history SET status = 'success' WHERE status IS NULL")


def downgrade() -> None:
    """Remove T6 fields from step_history."""
    op.drop_column('step_history', 'feedback')
    op.drop_column('step_history', 'parent_id')
    op.drop_column('step_history', 'generation_time_seconds')
    op.drop_column('step_history', 'error_message')
    op.drop_column('step_history', 'status')
