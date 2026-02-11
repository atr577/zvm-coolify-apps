"""T42: add template metrics support

Revision ID: c245dcc9af17
Revises: 865ed2397fb4
Create Date: 2026-02-10 17:19:00.436860

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c245dcc9af17'
down_revision: Union[str, Sequence[str], None] = '865ed2397fb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # approved_generations: add post_ids and post_urls JSON columns
    op.add_column('approved_generations', sa.Column('post_ids', sa.JSON(), nullable=True))
    op.add_column('approved_generations', sa.Column('post_urls', sa.JSON(), nullable=True))

    # video_metrics: add approved_generation_id FK, saves, reach, avg_watch_time_ms
    op.add_column('video_metrics', sa.Column('approved_generation_id', sa.Integer(), nullable=True))
    op.add_column('video_metrics', sa.Column('saves', sa.Integer(), server_default='0', nullable=True))
    op.add_column('video_metrics', sa.Column('reach', sa.Integer(), server_default='0', nullable=True))
    op.add_column('video_metrics', sa.Column('avg_watch_time_ms', sa.Integer(), nullable=True))

    # video_metrics: make video_id nullable, add FK, add CheckConstraint
    with op.batch_alter_table('video_metrics') as batch_op:
        batch_op.alter_column('video_id', existing_type=sa.INTEGER(), nullable=True)
        batch_op.create_index('ix_video_metrics_approved_generation_id', ['approved_generation_id'])
        batch_op.create_foreign_key(
            'fk_video_metrics_approved_generation',
            'approved_generations',
            ['approved_generation_id'], ['id'],
            ondelete='CASCADE'
        )
        batch_op.create_check_constraint(
            'ck_video_metrics_has_parent',
            'video_id IS NOT NULL OR approved_generation_id IS NOT NULL'
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('video_metrics') as batch_op:
        batch_op.drop_constraint('ck_video_metrics_has_parent', type_='check')
        batch_op.drop_constraint('fk_video_metrics_approved_generation', type_='foreignkey')
        batch_op.drop_index('ix_video_metrics_approved_generation_id')
        batch_op.alter_column('video_id', existing_type=sa.INTEGER(), nullable=False)

    op.drop_column('video_metrics', 'avg_watch_time_ms')
    op.drop_column('video_metrics', 'reach')
    op.drop_column('video_metrics', 'saves')
    op.drop_column('video_metrics', 'approved_generation_id')
    op.drop_column('approved_generations', 'post_urls')
    op.drop_column('approved_generations', 'post_ids')
