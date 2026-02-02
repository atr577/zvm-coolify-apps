"""add_publishing_schedule_models

Revision ID: f7d2e8c3a1b9
Revises: 4e5e1936c85c
Create Date: 2026-02-02 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7d2e8c3a1b9'
down_revision: Union[str, Sequence[str], None] = '4e5e1936c85c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create publishing_configs table
    op.create_table('publishing_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('days', sa.JSON(), nullable=False),
        sa.Column('preferred_time', sa.String(length=5), nullable=False, server_default='18:00'),
        sa.Column('depth_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id')
    )
    op.create_index(op.f('ix_publishing_configs_id'), 'publishing_configs', ['id'], unique=False)

    # Add timezone to projects
    op.add_column('projects', sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'))

    # Add publishing metadata prompts to template_settings
    op.add_column('template_settings', sa.Column('title_prompt', sa.Text(), nullable=True))
    op.add_column('template_settings', sa.Column('description_prompt', sa.Text(), nullable=True))
    op.add_column('template_settings', sa.Column('platform_rules', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop platform_rules, description_prompt, title_prompt from template_settings
    op.drop_column('template_settings', 'platform_rules')
    op.drop_column('template_settings', 'description_prompt')
    op.drop_column('template_settings', 'title_prompt')

    # Drop timezone from projects
    op.drop_column('projects', 'timezone')

    # Drop publishing_configs table
    op.drop_index(op.f('ix_publishing_configs_id'), table_name='publishing_configs')
    op.drop_table('publishing_configs')
