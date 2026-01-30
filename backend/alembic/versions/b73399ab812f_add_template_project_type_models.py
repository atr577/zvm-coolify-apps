"""add_template_project_type_models

Revision ID: b73399ab812f
Revises: 9225fd5377af
Create Date: 2026-01-29 14:59:56.481031

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b73399ab812f'
down_revision: Union[str, Sequence[str], None] = '9225fd5377af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add template project type models: TemplateSettings, VideoTemplate, Variant, TemplateGeneration."""

    # 1. Create template_settings table
    op.create_table('template_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('preprocessing_prompt', sa.Text(), nullable=False),
        sa.Column('image_prompt_template', sa.Text(), nullable=False),
        sa.Column('llm_model', sa.String(length=50), nullable=False, server_default='gpt-4o-mini'),
        sa.Column('image_model', sa.String(length=100), nullable=False, server_default='fal-ai/nano-banana-pro'),
        sa.Column('video_model', sa.String(length=100), nullable=False, server_default='fal-ai/veo3/fast/image-to-video'),
        sa.Column('image_aspect_ratio', sa.String(length=10), nullable=False, server_default='9:16'),
        sa.Column('csv_columns', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id')
    )
    op.create_index(op.f('ix_template_settings_id'), 'template_settings', ['id'], unique=False)

    # 2. Create video_templates table
    op.create_table('video_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_templates_id'), 'video_templates', ['id'], unique=False)

    # 3. Create variants table
    op.create_table('variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_variants_id'), 'variants', ['id'], unique=False)
    op.create_index('ix_variants_project_usage', 'variants', ['project_id', 'usage_count'], unique=False)

    # 4. Create template_generations table
    op.create_table('template_generations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('variant_id', sa.Integer(), nullable=True),
        sa.Column('video_template_id', sa.Integer(), nullable=True),
        sa.Column('llm_model', sa.String(length=50), nullable=False),
        sa.Column('image_model', sa.String(length=100), nullable=False),
        sa.Column('video_model', sa.String(length=100), nullable=False),
        sa.Column('preprocessing_result', sa.JSON(), nullable=True),
        sa.Column('image_prompt', sa.Text(), nullable=True),
        sa.Column('video_prompt', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('video_url', sa.String(length=500), nullable=True),
        sa.Column('image_path', sa.String(length=255), nullable=True),
        sa.Column('video_path', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('failed_at_step', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('llm_tokens_used', sa.Integer(), nullable=True),
        sa.Column('image_cost', sa.Float(), nullable=True),
        sa.Column('video_cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['variant_id'], ['variants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['video_template_id'], ['video_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_template_generations_id'), 'template_generations', ['id'], unique=False)


def downgrade() -> None:
    """Remove template project type models."""
    op.drop_index(op.f('ix_template_generations_id'), table_name='template_generations')
    op.drop_table('template_generations')

    op.drop_index('ix_variants_project_usage', table_name='variants')
    op.drop_index(op.f('ix_variants_id'), table_name='variants')
    op.drop_table('variants')

    op.drop_index(op.f('ix_video_templates_id'), table_name='video_templates')
    op.drop_table('video_templates')

    op.drop_index(op.f('ix_template_settings_id'), table_name='template_settings')
    op.drop_table('template_settings')
