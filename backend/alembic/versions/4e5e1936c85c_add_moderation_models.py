"""add_moderation_models

Revision ID: 4e5e1936c85c
Revises: 746e532489d0
Create Date: 2026-02-02 20:29:01.033487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e5e1936c85c'
down_revision: Union[str, Sequence[str], None] = '746e532489d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create approved_generations table
    op.create_table('approved_generations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('template_generation_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('approved_at', sa.DateTime(), nullable=False),
        sa.Column('publishing_metadata', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('platform_statuses', sa.JSON(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_generation_id'], ['template_generations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_generation_id')
    )
    op.create_index('ix_approved_gen_position', 'approved_generations', ['project_id', 'position'], unique=False)
    op.create_index('ix_approved_gen_project_status', 'approved_generations', ['project_id', 'status'], unique=False)
    op.create_index(op.f('ix_approved_generations_id'), 'approved_generations', ['id'], unique=False)

    # Create rejection_archive table
    op.create_table('rejection_archive',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('template_generation_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('rejected_by', sa.Integer(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_generation_id'], ['template_generations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_generation_id')
    )
    op.create_index(op.f('ix_rejection_archive_id'), 'rejection_archive', ['id'], unique=False)
    op.create_index('ix_rejection_project', 'rejection_archive', ['project_id'], unique=False)

    # Add regenerated column to template_generations
    op.add_column('template_generations', sa.Column('regenerated', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop regenerated column
    op.drop_column('template_generations', 'regenerated')

    # Drop rejection_archive table
    op.drop_index('ix_rejection_project', table_name='rejection_archive')
    op.drop_index(op.f('ix_rejection_archive_id'), table_name='rejection_archive')
    op.drop_table('rejection_archive')

    # Drop approved_generations table
    op.drop_index(op.f('ix_approved_generations_id'), table_name='approved_generations')
    op.drop_index('ix_approved_gen_project_status', table_name='approved_generations')
    op.drop_index('ix_approved_gen_position', table_name='approved_generations')
    op.drop_table('approved_generations')
