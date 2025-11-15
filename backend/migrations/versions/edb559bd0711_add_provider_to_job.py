"""Add provider field to translation_job

Revision ID: edb559bd0711
Revises: e1f2g3h4i5j6
Create Date: 2025-11-14 01:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'edb559bd0711'
down_revision = 'e1f2g3h4i5j6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Add provider column to translation_job table
    op.add_column('translation_job', sa.Column('provider', sa.String(50), nullable=True))

    # Set default value to 'ollama' for existing records
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE translation_job SET provider = 'ollama' WHERE provider IS NULL"))


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop provider column
    op.drop_column('translation_job', 'provider')
