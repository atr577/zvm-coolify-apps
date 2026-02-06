"""add discover_refinements table

Revision ID: c32bcffe4319
Revises: d03851d7ce10
Create Date: 2026-02-05 23:47:09.538159

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c32bcffe4319'
down_revision: Union[str, Sequence[str], None] = 'd03851d7ce10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add discover_refinements table for prompt refinement workflow."""
    op.create_table('discover_refinements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('original_concept', sa.Text(), nullable=False),
        sa.Column('relevant_blocks', sa.JSON(), nullable=False),
        sa.Column('blocks', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('refined_prompt', sa.Text(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('analysis_prompt_used', sa.Text(), nullable=True),
        sa.Column('analysis_response', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['project_id'], ['discover_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_discover_refinements_id'), 'discover_refinements', ['id'], unique=False)
    op.create_index(op.f('ix_discover_refinements_project_id'), 'discover_refinements', ['project_id'], unique=True)


def downgrade() -> None:
    """Drop discover_refinements table."""
    op.drop_index(op.f('ix_discover_refinements_project_id'), table_name='discover_refinements')
    op.drop_index(op.f('ix_discover_refinements_id'), table_name='discover_refinements')
    op.drop_table('discover_refinements')
