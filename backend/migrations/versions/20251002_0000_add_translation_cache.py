"""Add translation cache

Revision ID: add_translation_cache
Revises: 356ca67d7eba
Create Date: 2025-10-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_translation_cache'
down_revision: Union[str, None] = '356ca67d7eba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create translation_cache table
    op.create_table(
        'translation_cache',
        sa.Column('content_hash', sa.String(length=64), nullable=False, comment='SHA256 hash of source text, languages, and model'),
        sa.Column('source_text', sa.Text(), nullable=False, comment='Original text to translate'),
        sa.Column('translated_text', sa.Text(), nullable=False, comment='Translated text result'),
        sa.Column('source_lang', sa.String(length=10), nullable=False, comment='Source language code (BCP-47)'),
        sa.Column('target_lang', sa.String(length=10), nullable=False, comment='Target language code (BCP-47)'),
        sa.Column('model', sa.String(length=100), nullable=False, comment='Translation model name'),
        sa.Column('hit_count', sa.Integer(), nullable=False, comment='Number of times this cache entry was reused'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='When this translation was first cached'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=False, comment='When this cache entry was last accessed'),
        sa.PrimaryKeyConstraint('content_hash')
    )
    
    # Create indexes
    op.create_index('ix_translation_cache_content_hash', 'translation_cache', ['content_hash'], unique=False)
    op.create_index('ix_translation_cache_langs', 'translation_cache', ['source_lang', 'target_lang'], unique=False)
    op.create_index('ix_translation_cache_model', 'translation_cache', ['model'], unique=False)
    op.create_index('ix_translation_cache_last_used', 'translation_cache', ['last_used_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_translation_cache_last_used', table_name='translation_cache')
    op.drop_index('ix_translation_cache_model', table_name='translation_cache')
    op.drop_index('ix_translation_cache_langs', table_name='translation_cache')
    op.drop_index('ix_translation_cache_content_hash', table_name='translation_cache')
    
    # Drop table
    op.drop_table('translation_cache')
