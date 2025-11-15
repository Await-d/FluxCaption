"""Add multi-provider AI support

Revision ID: e1f2g3h4i5j6
Revises: d0e1f2g3h4i5
Create Date: 2025-01-14

This migration adds support for multiple AI providers (OpenAI, DeepSeek, Claude, etc.)
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone
import uuid

# revision identifiers, used by Alembic.
revision = 'e1f2g3h4i5j6'
down_revision = 'd0e1f2g3h4i5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Create AI provider configs table
    op.create_table(
        'ai_provider_configs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('provider_name', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('api_key', sa.Text(), nullable=True),
        sa.Column('base_url', sa.String(255), nullable=True),
        sa.Column('timeout', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('extra_config', sa.Text(), nullable=True),
        sa.Column('default_model', sa.String(100), nullable=True),
        sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_healthy', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('health_error', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_provider_enabled', 'ai_provider_configs', ['is_enabled'])
    op.create_index('idx_provider_priority', 'ai_provider_configs', ['priority'])

    # Create AI provider usage logs table
    op.create_table(
        'ai_provider_usage_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('provider_name', sa.String(50), nullable=False, index=True),
        sa.Column('model_name', sa.String(100), nullable=False, index=True),
        sa.Column('job_id', sa.String(36), nullable=True, index=True),
        sa.Column('user_id', sa.String(36), nullable=True, index=True),
        sa.Column('request_type', sa.String(20), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('input_cost', sa.Float(), nullable=True),
        sa.Column('output_cost', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('finish_reason', sa.String(50), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('is_error', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('prompt_preview', sa.Text(), nullable=True),
        sa.Column('response_preview', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_usage_provider_created', 'ai_provider_usage_logs', ['provider_name', 'created_at'])
    op.create_index('idx_usage_date', 'ai_provider_usage_logs', ['created_at'])
    op.create_index('idx_usage_cost', 'ai_provider_usage_logs', ['total_cost'])
    op.create_index('idx_usage_job', 'ai_provider_usage_logs', ['job_id'])

    # Create AI provider quotas table
    op.create_table(
        'ai_provider_quotas',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('provider_name', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('daily_limit', sa.Float(), nullable=True),
        sa.Column('monthly_limit', sa.Float(), nullable=True),
        sa.Column('daily_token_limit', sa.Integer(), nullable=True),
        sa.Column('monthly_token_limit', sa.Integer(), nullable=True),
        sa.Column('requests_per_minute', sa.Integer(), nullable=True),
        sa.Column('requests_per_hour', sa.Integer(), nullable=True),
        sa.Column('current_daily_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('current_monthly_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('current_daily_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_monthly_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('daily_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('monthly_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('alert_threshold_percent', sa.Integer(), nullable=False, server_default='80'),
        sa.Column('auto_disable_on_limit', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_alert_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Modify model_registry table to support multiple providers
    # First, check if we need to migrate existing data

    # Add provider column (nullable first for migration)
    op.add_column('model_registry', sa.Column('provider', sa.String(50), nullable=True))

    # Update existing records to use 'ollama' as provider
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE model_registry SET provider = 'ollama' WHERE provider IS NULL"))

    # Make provider column NOT NULL
    op.alter_column('model_registry', 'provider', nullable=False)

    # Drop old unique constraint on name (if exists)
    try:
        op.drop_constraint('model_registry_name_key', 'model_registry', type_='unique')
    except:
        # Constraint might not exist or have different name on different databases
        pass

    # Add new unique constraint on (provider, name)
    op.create_unique_constraint('uq_provider_model', 'model_registry', ['provider', 'name'])

    # Add new columns for cloud providers
    op.add_column('model_registry', sa.Column('context_length', sa.BigInteger(), nullable=True))
    op.add_column('model_registry', sa.Column('cost_input_per_1k', sa.Float(), nullable=True))
    op.add_column('model_registry', sa.Column('cost_output_per_1k', sa.Float(), nullable=True))
    op.add_column('model_registry', sa.Column('model_description', sa.Text(), nullable=True))

    # Add new indexes
    op.create_index('idx_model_provider_status', 'model_registry', ['provider', 'status'])

    # Insert default provider configurations using bind
    now = datetime.now(timezone.utc)

    providers_data = [
        {
            'id': str(uuid.uuid4()),
            'provider_name': 'ollama',
            'display_name': 'Ollama (Local)',
            'is_enabled': True,
            'priority': 1,
            'description': 'Local LLM deployment with Ollama',
        },
        {
            'id': str(uuid.uuid4()),
            'provider_name': 'openai',
            'display_name': 'OpenAI',
            'is_enabled': False,
            'priority': 2,
            'description': 'OpenAI GPT models (GPT-4, GPT-3.5, etc.)',
        },
        {
            'id': str(uuid.uuid4()),
            'provider_name': 'deepseek',
            'display_name': 'DeepSeek',
            'is_enabled': False,
            'priority': 3,
            'description': 'DeepSeek AI models (affordable and powerful)',
        },
        {
            'id': str(uuid.uuid4()),
            'provider_name': 'claude',
            'display_name': 'Claude (Anthropic)',
            'is_enabled': False,
            'priority': 4,
            'description': 'Anthropic Claude models (Opus, Sonnet, Haiku)',
        },
        {
            'id': str(uuid.uuid4()),
            'provider_name': 'gemini',
            'display_name': 'Gemini (Google)',
            'is_enabled': False,
            'priority': 5,
            'description': 'Google Gemini models',
        },
        {
            'id': str(uuid.uuid4()),
            'provider_name': 'zhipu',
            'display_name': '智谱AI (GLM)',
            'is_enabled': False,
            'priority': 6,
            'description': '智谱AI GLM models - Chinese-optimized',
        },
        {
            'id': str(uuid.uuid4()),
            'provider_name': 'moonshot',
            'display_name': 'Moonshot AI (Kimi)',
            'is_enabled': False,
            'priority': 7,
            'description': 'Moonshot Kimi models - Super long context',
        },
        {
            'id': str(uuid.uuid4()),
            'provider_name': 'custom_openai',
            'display_name': 'Custom OpenAI Compatible',
            'is_enabled': False,
            'priority': 8,
            'description': 'Custom OpenAI-compatible endpoint (OpenRouter, LocalAI, vLLM, etc.)',
        },
    ]

    # Insert providers using parameterized queries
    for provider in providers_data:
        conn.execute(
            sa.text("""
                INSERT INTO ai_provider_configs
                (id, provider_name, display_name, is_enabled, priority, description,
                 timeout, is_healthy, created_at, updated_at)
                VALUES
                (:id, :provider_name, :display_name, :is_enabled, :priority, :description,
                 300, 0, :created_at, :updated_at)
            """),
            {
                **provider,
                'created_at': now,
                'updated_at': now,
            }
        )


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop AI provider quotas table
    op.drop_table('ai_provider_quotas')

    # Drop AI provider usage logs table
    op.drop_index('idx_usage_job', 'ai_provider_usage_logs')
    op.drop_index('idx_usage_cost', 'ai_provider_usage_logs')
    op.drop_index('idx_usage_date', 'ai_provider_usage_logs')
    op.drop_index('idx_usage_provider_created', 'ai_provider_usage_logs')
    op.drop_table('ai_provider_usage_logs')

    # Drop AI provider configs table
    op.drop_index('idx_provider_priority', 'ai_provider_configs')
    op.drop_index('idx_provider_enabled', 'ai_provider_configs')
    op.drop_table('ai_provider_configs')

    # Revert model_registry changes
    op.drop_index('idx_model_provider_status', 'model_registry')
    op.drop_column('model_registry', 'model_description')
    op.drop_column('model_registry', 'cost_output_per_1k')
    op.drop_column('model_registry', 'cost_input_per_1k')
    op.drop_column('model_registry', 'context_length')

    # Drop new unique constraint
    op.drop_constraint('uq_provider_model', 'model_registry', type_='unique')

    # Restore old unique constraint on name
    op.create_unique_constraint(None, 'model_registry', ['name'])

    # Drop provider column
    op.drop_column('model_registry', 'provider')
