"""add_auto_translation_rule_table

Revision ID: a7b8c9d0e1f2
Revises: f3a4b9c8d2e1
Create Date: 2025-10-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f3a4b9c8d2e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create auto_translation_rule table
    op.create_table(
        'auto_translation_rule',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('jellyfin_library_ids', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('source_lang', sa.String(length=20), nullable=True),
        sa.Column('target_langs', sa.Text(), nullable=False),
        sa.Column('auto_start', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('ix_auto_translation_rule_user_id', 'auto_translation_rule', ['user_id'])
    op.create_index('ix_auto_translation_rule_created_at', 'auto_translation_rule', ['created_at'])


def downgrade() -> None:
    # Drop indexes and table
    op.drop_index('ix_auto_translation_rule_created_at', table_name='auto_translation_rule')
    op.drop_index('ix_auto_translation_rule_user_id', table_name='auto_translation_rule')
    op.drop_table('auto_translation_rule')
