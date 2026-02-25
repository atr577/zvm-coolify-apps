"""add_youtube_account_id_to_projects

Revision ID: c7e9f2a4b1d3
Revises: 5b6f057a900e
Create Date: 2026-02-25

"""
from alembic import op
import sqlalchemy as sa

revision = 'c7e9f2a4b1d3'
down_revision = '5b6f057a900e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column(
        'youtube_account_id',
        sa.Integer(),
        sa.ForeignKey('youtube_accounts.id', ondelete='SET NULL'),
        nullable=True,
    ))
    op.create_index('ix_projects_youtube_account_id', 'projects', ['youtube_account_id'])


def downgrade() -> None:
    op.drop_index('ix_projects_youtube_account_id', table_name='projects')
    op.drop_column('projects', 'youtube_account_id')
