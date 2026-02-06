"""add audio_library and discover_audio_variants tables

Revision ID: a1d15a15d360
Revises: c32bcffe4319
Create Date: 2026-02-06 14:31:44.935044

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1d15a15d360'
down_revision: Union[str, Sequence[str], None] = 'c32bcffe4319'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add audio_library table, discover_audio_variants table, and audio fields on projects."""
    # 1. audio_library table
    op.create_table('audio_library',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_discover_project_id', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('mood', sa.String(length=20), nullable=True),
        sa.Column('use_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['source_discover_project_id'], ['discover_projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audio_library_id'), 'audio_library', ['id'], unique=False)
    op.create_index(op.f('ix_audio_library_workspace_id'), 'audio_library', ['workspace_id'], unique=False)
    op.create_index('ix_audio_library_workspace_created', 'audio_library', ['workspace_id', 'created_at'], unique=False)
    op.create_index('ix_audio_library_workspace_mood', 'audio_library', ['workspace_id', 'mood'], unique=False)

    # 2. discover_audio_variants table
    op.create_table('discover_audio_variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('audio_type', sa.String(length=20), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('prompt_mode', sa.String(length=10), nullable=False, server_default='manual'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_url', sa.String(length=500), nullable=True),
        sa.Column('full_duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('detected_hooks', sa.JSON(), nullable=True),
        sa.Column('hook_start_ms', sa.Integer(), nullable=True),
        sa.Column('hook_end_ms', sa.Integer(), nullable=True),
        sa.Column('trimmed_file_path', sa.String(length=500), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('library_item_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['library_item_id'], ['audio_library.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['discover_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_discover_audio_variants_id'), 'discover_audio_variants', ['id'], unique=False)
    op.create_index(op.f('ix_discover_audio_variants_project_id'), 'discover_audio_variants', ['project_id'], unique=False)

    # 3. Add audio fields to discover_projects
    op.add_column('discover_projects', sa.Column('audio_mode', sa.String(length=20), nullable=True))
    op.add_column('discover_projects', sa.Column('selected_audio_variant_id', sa.Integer(), nullable=True))
    # Note: SQLite doesn't support ALTER FK, so we skip FK constraint creation here.
    # The FK is enforced at the ORM level via the model relationship.

    # 4. Add audio_source_id to projects (Template)
    op.add_column('projects', sa.Column('audio_source_id', sa.Integer(), nullable=True))
    # Same: FK enforced at ORM level for SQLite compatibility.


def downgrade() -> None:
    """Remove audio tables and fields."""
    # 4. Remove audio_source_id from projects
    op.drop_column('projects', 'audio_source_id')

    # 3. Remove audio fields from discover_projects
    op.drop_column('discover_projects', 'selected_audio_variant_id')
    op.drop_column('discover_projects', 'audio_mode')

    # 2. Drop discover_audio_variants
    op.drop_index(op.f('ix_discover_audio_variants_project_id'), table_name='discover_audio_variants')
    op.drop_index(op.f('ix_discover_audio_variants_id'), table_name='discover_audio_variants')
    op.drop_table('discover_audio_variants')

    # 1. Drop audio_library
    op.drop_index('ix_audio_library_workspace_mood', table_name='audio_library')
    op.drop_index(op.f('ix_audio_library_workspace_id'), table_name='audio_library')
    op.drop_index('ix_audio_library_workspace_created', table_name='audio_library')
    op.drop_index(op.f('ix_audio_library_id'), table_name='audio_library')
    op.drop_table('audio_library')
