"""add_discover_workflow_tables

Revision ID: 4b0c1b99979d
Revises: 99bc482a8954
Create Date: 2026-02-04 21:06:22.026650

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4b0c1b99979d'
down_revision: Union[str, Sequence[str], None] = '99bc482a8954'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add discover workflow tables + source_discover_id to template_settings."""

    # 1. discover_projects
    op.create_table(
        'discover_projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('concept', sa.Text(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('stage', sa.String(length=20), nullable=False, server_default='images'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('current_image_round', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_video_round', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('image_model', sa.String(length=100), nullable=False, server_default='fal-ai/flux-pro/v1.1'),
        sa.Column('video_model', sa.String(length=100), nullable=False, server_default='fal-ai/veo3/fast/image-to-video'),
        sa.Column('image_aspect_ratio', sa.String(length=10), nullable=False, server_default='9:16'),
        sa.Column('video_duration', sa.String(length=10), nullable=False, server_default='6s'),
        sa.Column('finalist_image_item_id', sa.Integer(), nullable=True),
        sa.Column('finalist_video_item_id', sa.Integer(), nullable=True),
        sa.Column('created_project_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_discover_projects_id'), 'discover_projects', ['id'], unique=False)
    op.create_index(op.f('ix_discover_projects_workspace_id'), 'discover_projects', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_discover_projects_user_id'), 'discover_projects', ['user_id'], unique=False)

    # 2. discover_rounds
    op.create_table(
        'discover_rounds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('round_type', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('system_prompt_used', sa.Text(), nullable=True),
        sa.Column('user_prompt_used', sa.Text(), nullable=True),
        sa.Column('generated_prompts', sa.JSON(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('total_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('selected_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rejected_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['discover_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'round_number', 'round_type', name='uq_discover_round'),
    )
    op.create_index(op.f('ix_discover_rounds_id'), 'discover_rounds', ['id'], unique=False)
    op.create_index(op.f('ix_discover_rounds_project_id'), 'discover_rounds', ['project_id'], unique=False)

    # 3. discover_items
    op.create_table(
        'discover_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('round_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('source_image_item_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('fal_request_id', sa.String(length=100), nullable=True),
        sa.Column('result_url', sa.String(length=500), nullable=True),
        sa.Column('local_path', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('selection', sa.String(length=20), nullable=False, server_default='unreviewed'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['round_id'], ['discover_rounds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_image_item_id'], ['discover_items.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_discover_items_id'), 'discover_items', ['id'], unique=False)
    op.create_index(op.f('ix_discover_items_round_id'), 'discover_items', ['round_id'], unique=False)

    # 4. discover_extractions
    op.create_table(
        'discover_extractions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('winning_image_prompt', sa.Text(), nullable=False),
        sa.Column('winning_video_prompt', sa.Text(), nullable=True),
        sa.Column('base_prompt', sa.Text(), nullable=False),
        sa.Column('variation_prompt', sa.Text(), nullable=False),
        sa.Column('slot_names', sa.JSON(), nullable=True),
        sa.Column('slot_examples', sa.JSON(), nullable=True),
        sa.Column('edited_base_prompt', sa.Text(), nullable=True),
        sa.Column('edited_variation_prompt', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['discover_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id'),
    )
    op.create_index(op.f('ix_discover_extractions_id'), 'discover_extractions', ['id'], unique=False)

    # 5. Add finalist FKs to discover_projects (after discover_items exists)
    op.create_foreign_key(
        'fk_discover_projects_finalist_image',
        'discover_projects', 'discover_items',
        ['finalist_image_item_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_discover_projects_finalist_video',
        'discover_projects', 'discover_items',
        ['finalist_video_item_id'], ['id'],
        ondelete='SET NULL',
    )

    # 6. Add source_discover_id to template_settings
    op.add_column(
        'template_settings',
        sa.Column('source_discover_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_template_settings_source_discover',
        'template_settings', 'discover_projects',
        ['source_discover_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Remove discover workflow tables."""
    # Remove FK from template_settings
    op.drop_constraint('fk_template_settings_source_discover', 'template_settings', type_='foreignkey')
    op.drop_column('template_settings', 'source_discover_id')

    # Remove finalist FKs from discover_projects
    op.drop_constraint('fk_discover_projects_finalist_video', 'discover_projects', type_='foreignkey')
    op.drop_constraint('fk_discover_projects_finalist_image', 'discover_projects', type_='foreignkey')

    # Drop tables in reverse order
    op.drop_index(op.f('ix_discover_extractions_id'), table_name='discover_extractions')
    op.drop_table('discover_extractions')

    op.drop_index(op.f('ix_discover_items_round_id'), table_name='discover_items')
    op.drop_index(op.f('ix_discover_items_id'), table_name='discover_items')
    op.drop_table('discover_items')

    op.drop_index(op.f('ix_discover_rounds_project_id'), table_name='discover_rounds')
    op.drop_index(op.f('ix_discover_rounds_id'), table_name='discover_rounds')
    op.drop_table('discover_rounds')

    op.drop_index(op.f('ix_discover_projects_user_id'), table_name='discover_projects')
    op.drop_index(op.f('ix_discover_projects_workspace_id'), table_name='discover_projects')
    op.drop_index(op.f('ix_discover_projects_id'), table_name='discover_projects')
    op.drop_table('discover_projects')
