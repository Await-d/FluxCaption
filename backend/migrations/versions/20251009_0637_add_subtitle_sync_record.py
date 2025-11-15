"""add_subtitle_sync_record

Revision ID: d0e1f2g3h4i5
Revises: c9d0e1f2g3h4
Create Date: 2025-10-09 06:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0e1f2g3h4i5'
down_revision: Union[str, None] = 'c9d0e1f2g3h4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add subtitle_sync_records table for tracking subtitle synchronization."""

    op.create_table(
        'subtitle_sync_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('subtitle_id', sa.String(length=36), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('sync_mode', sa.String(length=32), nullable=False),
        sa.Column('total_lines', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('synced_lines', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_lines', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_lines', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('paired_subtitle_id', sa.String(length=36), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subtitle_id'], ['subtitles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['media_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['paired_subtitle_id'], ['subtitles.id'], ondelete='SET NULL'),
    )

    # Create indexes for better query performance
    op.create_index('ix_subtitle_sync_subtitle', 'subtitle_sync_records', ['subtitle_id'])
    op.create_index('ix_subtitle_sync_asset', 'subtitle_sync_records', ['asset_id'])
    op.create_index('ix_subtitle_sync_status', 'subtitle_sync_records', ['status'])
    op.create_index('ix_subtitle_sync_created', 'subtitle_sync_records', ['created_at'])


def downgrade() -> None:
    """Remove subtitle_sync_records table."""

    op.drop_index('ix_subtitle_sync_created', table_name='subtitle_sync_records')
    op.drop_index('ix_subtitle_sync_status', table_name='subtitle_sync_records')
    op.drop_index('ix_subtitle_sync_asset', table_name='subtitle_sync_records')
    op.drop_index('ix_subtitle_sync_subtitle', table_name='subtitle_sync_records')
    op.drop_table('subtitle_sync_records')

