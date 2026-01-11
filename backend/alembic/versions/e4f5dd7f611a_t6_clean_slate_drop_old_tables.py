"""t6_clean_slate_drop_old_tables

Revision ID: e4f5dd7f611a
Revises: 0fa8369469c8
Create Date: 2026-01-11

T6.1: Clean slate - delete all videos and drop old workflow tables.
This is a destructive migration - all video data will be lost.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5dd7f611a'
down_revision: Union[str, Sequence[str], None] = '0fa8369469c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Delete all video data and drop old workflow tables."""
    # Delete all data from related tables (order matters for FK constraints)
    op.execute("DELETE FROM step_history")
    op.execute("DELETE FROM video_metrics")
    op.execute("DELETE FROM publish_results")

    # These tables may not exist in all DBs, use IF EXISTS
    op.execute("DELETE FROM validation_results WHERE 1=1")
    op.execute("DELETE FROM variants WHERE 1=1")
    op.execute("DELETE FROM step_attempts WHERE 1=1")
    op.execute("DELETE FROM workflow_steps WHERE 1=1")
    op.execute("DELETE FROM videos")

    # Drop old workflow tables
    op.execute("DROP TABLE IF EXISTS variants")
    op.execute("DROP TABLE IF EXISTS step_attempts")
    op.execute("DROP TABLE IF EXISTS validation_results")
    op.execute("DROP TABLE IF EXISTS workflow_steps")


def downgrade() -> None:
    """
    Cannot restore deleted data.
    Tables can be recreated by reverting to older migrations if needed.
    """
    # Recreate old tables structure (empty)
    op.create_table(
        'workflow_steps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('video_id', sa.Integer(), sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('validation_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_validation_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('selected_variant_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'validation_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('step_id', sa.Integer(), sa.ForeignKey('workflow_steps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('criteria_results', sa.JSON(), nullable=True),
        sa.Column('warnings', sa.JSON(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'step_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('step_id', sa.Integer(), sa.ForeignKey('workflow_steps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'variants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('attempt_id', sa.Integer(), sa.ForeignKey('step_attempts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('variant_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('is_selected', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
