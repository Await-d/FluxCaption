"""add_checkpoint_fields_to_translation_job

Revision ID: b8c9d0e1f2g3
Revises: a7b8c9d0e1f2
Create Date: 2025-10-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2g3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add checkpoint/resume support fields to translation_job table."""

    # Add ASR output path field
    op.add_column(
        'translation_job',
        sa.Column('asr_output_path', sa.String(length=1024), nullable=True)
    )

    # Add completed phases field (JSON array)
    op.add_column(
        'translation_job',
        sa.Column('completed_phases', sa.Text(), nullable=True)
    )

    # Add completed target languages field (JSON array)
    op.add_column(
        'translation_job',
        sa.Column('completed_target_langs', sa.Text(), nullable=True)
    )

    # Add last checkpoint timestamp
    op.add_column(
        'translation_job',
        sa.Column('last_checkpoint_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove checkpoint/resume support fields from translation_job table."""

    op.drop_column('translation_job', 'last_checkpoint_at')
    op.drop_column('translation_job', 'completed_target_langs')
    op.drop_column('translation_job', 'completed_phases')
    op.drop_column('translation_job', 'asr_output_path')
