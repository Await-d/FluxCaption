"""Add job pause and resume support

Revision ID: f3g4h5i6j7k8
Revises: e1f2g3h4i5j6
Create Date: 2025-11-15

This migration adds pause/resume functionality for translation jobs when quota limits are exceeded.
Jobs can be automatically paused and resumed when daily/monthly quotas reset.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f3g4h5i6j7k8'
down_revision = 'e1f2g3h4i5j6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Add pause/resume fields to translation_jobs table
    op.add_column('translation_jobs',
        sa.Column('pause_reason', sa.String(64), nullable=True)
    )
    op.add_column('translation_jobs',
        sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('translation_jobs',
        sa.Column('resume_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Create index for paused jobs to efficiently find resumable jobs
    # Use conditional index for PostgreSQL (more efficient), regular index for others
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'postgresql':
        # PostgreSQL supports partial indexes with WHERE clause
        op.create_index(
            'idx_jobs_paused_resume',
            'translation_jobs',
            ['status', 'resume_at'],
            postgresql_where=sa.text("status = 'paused'")
        )
    else:
        # Other databases use regular index
        # Note: MySQL, SQLite, SQL Server will index all rows
        op.create_index(
            'idx_jobs_paused_resume',
            'translation_jobs',
            ['status', 'resume_at']
        )


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop index
    op.drop_index('idx_jobs_paused_resume', table_name='translation_jobs')

    # Remove columns
    op.drop_column('translation_jobs', 'resume_at')
    op.drop_column('translation_jobs', 'paused_at')
    op.drop_column('translation_jobs', 'pause_reason')
