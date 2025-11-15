"""add setting change history

Revision ID: g4h5i6j7k8l9
Revises: f3g4h5i6j7k8
Create Date: 2025-11-15 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g4h5i6j7k8l9'
down_revision: Union[str, None] = 'f3g4h5i6j7k8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add setting change history table."""
    op.create_table(
        'setting_change_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('setting_key', sa.String(255), nullable=False),
        sa.Column('old_value', sa.String(500), nullable=True),
        sa.Column('new_value', sa.String(500), nullable=False),
        sa.Column('changed_by', sa.String(255), nullable=False),
        sa.Column('change_reason', sa.Text(), nullable=True),  # Unbounded text
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create index for efficient queries
    op.create_index(
        'idx_setting_history_key',
        'setting_change_history',
        ['setting_key', 'created_at']
    )


def downgrade() -> None:
    """Remove setting change history table."""
    op.drop_index('idx_setting_history_key', table_name='setting_change_history')
    op.drop_table('setting_change_history')
