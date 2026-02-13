"""rename publishing meta prompts and add hashtags

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '801cd2441711'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('template_settings') as batch_op:
        batch_op.alter_column('title_prompt', new_column_name='meta_title_prompt')
        batch_op.alter_column('description_prompt', new_column_name='meta_description_prompt')
        batch_op.drop_column('platform_rules')
    op.add_column('template_settings', sa.Column('meta_hashtags_prompt', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('template_settings', 'meta_hashtags_prompt')
    with op.batch_alter_table('template_settings') as batch_op:
        batch_op.alter_column('meta_description_prompt', new_column_name='description_prompt')
        batch_op.alter_column('meta_title_prompt', new_column_name='title_prompt')
    op.add_column('template_settings', sa.Column('platform_rules', sa.JSON(), nullable=True))
