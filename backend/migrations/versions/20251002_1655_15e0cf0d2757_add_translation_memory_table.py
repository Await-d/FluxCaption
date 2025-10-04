"""add_translation_memory_table

Revision ID: 15e0cf0d2757
Revises: 30a7524f39aa
Create Date: 2025-10-02 16:55:56.468970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15e0cf0d2757'
down_revision: Union[str, None] = '30a7524f39aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create translation_memory table
    op.create_table(
        'translation_memory',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('subtitle_id', sa.CHAR(36), nullable=True),
        sa.Column('asset_id', sa.CHAR(36), nullable=True),
        sa.Column('source_text', sa.Text(), nullable=False),
        sa.Column('target_text', sa.Text(), nullable=False),
        sa.Column('source_lang', sa.String(length=20), nullable=False),
        sa.Column('target_lang', sa.String(length=20), nullable=False),
        sa.Column('context', sa.String(length=512), nullable=True),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.Float(), nullable=True),
        sa.Column('end_time', sa.Float(), nullable=True),
        sa.Column('word_count_source', sa.Integer(), nullable=True),
        sa.Column('word_count_target', sa.Integer(), nullable=True),
        sa.Column('translation_model', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['media_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subtitle_id'], ['subtitles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_tm_lang_pair', 'translation_memory', ['source_lang', 'target_lang'])
    op.create_index('ix_tm_subtitle', 'translation_memory', ['subtitle_id'])
    op.create_index('ix_tm_asset', 'translation_memory', ['asset_id'])
    op.create_index('ix_tm_created', 'translation_memory', ['created_at'])
    op.create_index('ix_translation_memory_asset_id', 'translation_memory', ['asset_id'])
    op.create_index('ix_translation_memory_source_lang', 'translation_memory', ['source_lang'])
    op.create_index('ix_translation_memory_subtitle_id', 'translation_memory', ['subtitle_id'])
    op.create_index('ix_translation_memory_target_lang', 'translation_memory', ['target_lang'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_translation_memory_target_lang', table_name='translation_memory')
    op.drop_index('ix_translation_memory_subtitle_id', table_name='translation_memory')
    op.drop_index('ix_translation_memory_source_lang', table_name='translation_memory')
    op.drop_index('ix_translation_memory_asset_id', table_name='translation_memory')
    op.drop_index('ix_tm_created', table_name='translation_memory')
    op.drop_index('ix_tm_asset', table_name='translation_memory')
    op.drop_index('ix_tm_subtitle', table_name='translation_memory')
    op.drop_index('ix_tm_lang_pair', table_name='translation_memory')

    # Drop table
    op.drop_table('translation_memory')
