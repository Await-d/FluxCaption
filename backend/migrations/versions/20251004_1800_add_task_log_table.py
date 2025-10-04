"""add_task_log_table

Revision ID: c9d0e1f2g3h4
Revises: b8c9d0e1f2g3
Create Date: 2025-10-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2g3h4'
down_revision: Union[str, None] = 'b8c9d0e1f2g3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add task_log table for storing job execution logs."""

    op.create_table(
        'task_log',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('phase', sa.String(length=16), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('progress', sa.Float(), nullable=False),
        sa.Column('completed', sa.Integer(), nullable=True),
        sa.Column('total', sa.Integer(), nullable=True),
        sa.Column('extra_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('idx_task_log_job_timestamp', 'task_log', ['job_id', 'timestamp'])
    op.create_index('idx_task_log_timestamp', 'task_log', ['timestamp'])
    op.create_index(op.f('ix_task_log_job_id'), 'task_log', ['job_id'])


def downgrade() -> None:
    """Remove task_log table."""

    op.drop_index(op.f('ix_task_log_job_id'), table_name='task_log')
    op.drop_index('idx_task_log_timestamp', table_name='task_log')
    op.drop_index('idx_task_log_job_timestamp', table_name='task_log')
    op.drop_table('task_log')
