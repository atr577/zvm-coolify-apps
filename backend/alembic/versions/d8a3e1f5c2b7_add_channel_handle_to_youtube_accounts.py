"""add_channel_handle_to_youtube_accounts

Revision ID: d8a3e1f5c2b7
Revises: c7e9f2a4b1d3
Create Date: 2026-02-25

"""
from alembic import op
import sqlalchemy as sa

revision = 'd8a3e1f5c2b7'
down_revision = 'c7e9f2a4b1d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('youtube_accounts', sa.Column('channel_handle', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('youtube_accounts', 'channel_handle')
