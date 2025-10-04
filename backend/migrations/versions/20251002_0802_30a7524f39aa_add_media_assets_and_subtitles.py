"""add_media_assets_and_subtitles

Revision ID: 30a7524f39aa
Revises: add_translation_cache
Create Date: 2025-10-02 08:02:18.410802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.models.types import GUID


# revision identifiers, used by Alembic.
revision: str = '30a7524f39aa'
down_revision: Union[str, None] = 'add_translation_cache'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Create media_assets table ###
    op.create_table('media_assets',
    sa.Column('item_id', sa.String(length=64), nullable=False),
    sa.Column('library_id', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=512), nullable=False),
    sa.Column('path', sa.String(length=1024), nullable=True),
    sa.Column('type', sa.String(length=32), nullable=False),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('checksum', sa.String(length=64), nullable=True),
    sa.Column('id', GUID(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_assets_item_id'), 'media_assets', ['item_id'], unique=True)
    op.create_index(op.f('ix_media_assets_library_id'), 'media_assets', ['library_id'], unique=False)
    op.create_index('ix_media_assets_library_created', 'media_assets', ['library_id', 'created_at'], unique=False)
    op.create_index('ix_media_assets_type', 'media_assets', ['type'], unique=False)

    # ### Create media_audio_langs table ###
    op.create_table('media_audio_langs',
    sa.Column('asset_id', GUID(length=36), nullable=False),
    sa.Column('lang', sa.String(length=20), nullable=False),
    sa.Column('codec', sa.String(length=32), nullable=True),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('id', GUID(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['media_assets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_audio_langs_asset_id'), 'media_audio_langs', ['asset_id'], unique=False)
    op.create_index('ix_media_audio_langs_asset_lang', 'media_audio_langs', ['asset_id', 'lang'], unique=True)
    op.create_index('ix_media_audio_langs_lang', 'media_audio_langs', ['lang'], unique=False)

    # ### Create media_subtitle_langs table ###
    op.create_table('media_subtitle_langs',
    sa.Column('asset_id', GUID(length=36), nullable=False),
    sa.Column('lang', sa.String(length=20), nullable=False),
    sa.Column('codec', sa.String(length=32), nullable=True),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('is_forced', sa.Boolean(), nullable=False),
    sa.Column('is_external', sa.Boolean(), nullable=False),
    sa.Column('id', GUID(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['media_assets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_subtitle_langs_asset_id'), 'media_subtitle_langs', ['asset_id'], unique=False)
    op.create_index('ix_media_subtitle_langs_asset_lang', 'media_subtitle_langs', ['asset_id', 'lang'], unique=False)
    op.create_index('ix_media_subtitle_langs_lang', 'media_subtitle_langs', ['lang'], unique=False)
    op.create_index('ix_media_subtitle_langs_external', 'media_subtitle_langs', ['is_external'], unique=False)

    # ### Create subtitles table ###
    op.create_table('subtitles',
    sa.Column('asset_id', GUID(length=36), nullable=True),
    sa.Column('lang', sa.String(length=20), nullable=False),
    sa.Column('format', sa.String(length=16), nullable=False),
    sa.Column('storage_path', sa.String(length=1024), nullable=False),
    sa.Column('origin', sa.String(length=16), nullable=False),
    sa.Column('source_lang', sa.String(length=20), nullable=True),
    sa.Column('is_uploaded', sa.Boolean(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('writeback_mode', sa.String(length=16), nullable=True),
    sa.Column('word_count', sa.Integer(), nullable=True),
    sa.Column('line_count', sa.Integer(), nullable=True),
    sa.Column('id', GUID(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['media_assets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subtitles_asset_id'), 'subtitles', ['asset_id'], unique=False)
    op.create_index(op.f('ix_subtitles_lang'), 'subtitles', ['lang'], unique=False)
    op.create_index('ix_subtitles_asset_lang', 'subtitles', ['asset_id', 'lang'], unique=False)
    op.create_index('ix_subtitles_origin', 'subtitles', ['origin'], unique=False)
    op.create_index('ix_subtitles_uploaded', 'subtitles', ['is_uploaded'], unique=False)
    op.create_index('ix_subtitles_created', 'subtitles', ['created_at'], unique=False)


def downgrade() -> None:
    # ### Drop tables in reverse order ###
    op.drop_index('ix_subtitles_created', table_name='subtitles')
    op.drop_index('ix_subtitles_uploaded', table_name='subtitles')
    op.drop_index('ix_subtitles_origin', table_name='subtitles')
    op.drop_index('ix_subtitles_asset_lang', table_name='subtitles')
    op.drop_index(op.f('ix_subtitles_lang'), table_name='subtitles')
    op.drop_index(op.f('ix_subtitles_asset_id'), table_name='subtitles')
    op.drop_table('subtitles')

    op.drop_index('ix_media_subtitle_langs_external', table_name='media_subtitle_langs')
    op.drop_index('ix_media_subtitle_langs_lang', table_name='media_subtitle_langs')
    op.drop_index('ix_media_subtitle_langs_asset_lang', table_name='media_subtitle_langs')
    op.drop_index(op.f('ix_media_subtitle_langs_asset_id'), table_name='media_subtitle_langs')
    op.drop_table('media_subtitle_langs')

    op.drop_index('ix_media_audio_langs_lang', table_name='media_audio_langs')
    op.drop_index('ix_media_audio_langs_asset_lang', table_name='media_audio_langs')
    op.drop_index(op.f('ix_media_audio_langs_asset_id'), table_name='media_audio_langs')
    op.drop_table('media_audio_langs')

    op.drop_index('ix_media_assets_type', table_name='media_assets')
    op.drop_index('ix_media_assets_library_created', table_name='media_assets')
    op.drop_index(op.f('ix_media_assets_library_id'), table_name='media_assets')
    op.drop_index(op.f('ix_media_assets_item_id'), table_name='media_assets')
    op.drop_table('media_assets')
