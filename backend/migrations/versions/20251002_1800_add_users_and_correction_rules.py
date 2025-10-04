"""add_users_and_correction_rules_tables

Revision ID: f3a4b9c8d2e1
Revises: 15e0cf0d2757
Create Date: 2025-10-02 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a4b9c8d2e1'
down_revision: Union[str, None] = '15e0cf0d2757'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for users table
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # Create correction_rules table
    op.create_table(
        'correction_rules',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('source_pattern', sa.Text(), nullable=False),
        sa.Column('target_text', sa.Text(), nullable=False),
        sa.Column('is_regex', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_case_sensitive', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('source_lang', sa.String(length=10), nullable=True),
        sa.Column('target_lang', sa.String(length=10), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for correction_rules table
    op.create_index('ix_correction_rules_is_active', 'correction_rules', ['is_active'])


def downgrade() -> None:
    # Drop correction_rules table and indexes
    op.drop_index('ix_correction_rules_is_active', table_name='correction_rules')
    op.drop_table('correction_rules')

    # Drop users table and indexes
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
