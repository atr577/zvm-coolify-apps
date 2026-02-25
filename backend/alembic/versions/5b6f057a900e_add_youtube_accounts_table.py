"""add_youtube_accounts_table

Revision ID: 5b6f057a900e
Revises: a1b2c3d4e5f6
Create Date: 2026-02-25 21:53:15.018632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b6f057a900e'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'youtube_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('google_account_id', sa.String(255), nullable=False),
        sa.Column('google_email', sa.String(255), nullable=False),
        sa.Column('channel_id', sa.String(255), nullable=False),
        sa.Column('channel_title', sa.String(255), nullable=False),
        sa.Column('channel_thumbnail_url', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('token_expiry', sa.DateTime(), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.Column('token_status', sa.String(50), nullable=True),
        sa.Column('last_token_refresh', sa.DateTime(), nullable=True),
        sa.Column('linked_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_youtube_accounts_id', 'youtube_accounts', ['id'], unique=False)
    op.create_index('ix_youtube_accounts_google_account_id', 'youtube_accounts', ['google_account_id'], unique=True)
    op.create_index('ix_youtube_accounts_channel_id', 'youtube_accounts', ['channel_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_youtube_accounts_channel_id', table_name='youtube_accounts')
    op.drop_index('ix_youtube_accounts_google_account_id', table_name='youtube_accounts')
    op.drop_index('ix_youtube_accounts_id', table_name='youtube_accounts')
    op.drop_table('youtube_accounts')
