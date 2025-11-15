"""Add AI model configuration table

Revision ID: e2f537e4eb44
Revises: edb559bd0711
Create Date: 2025-11-15 00:20

This migration adds the ai_model_configs table for managing models and pricing.
Includes automatic handling of database inconsistencies.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = 'e2f537e4eb44'
down_revision = 'edb559bd0711'
branch_labels = None
depends_on = None


def table_exists(inspector, table_name):
    """Check if table exists in database."""
    return table_name in inspector.get_table_names()


def index_exists(inspector, table_name, index_name):
    """Check if index exists on table."""
    try:
        indexes = inspector.get_indexes(table_name)
        return any(idx['name'] == index_name for idx in indexes)
    except Exception:
        return False


def foreign_key_exists(inspector, table_name, fk_name):
    """Check if foreign key exists on table."""
    try:
        fks = inspector.get_foreign_keys(table_name)
        return any(fk.get('name') == fk_name for fk in fks)
    except Exception:
        return False


def upgrade() -> None:
    """Upgrade database schema with automatic inconsistency resolution."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # Step 1: Create table if it doesn't exist
    if not table_exists(inspector, 'ai_model_configs'):
        print("Creating ai_model_configs table...")
        op.create_table(
            'ai_model_configs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('provider_name', sa.String(50), nullable=False),
            sa.Column('model_name', sa.String(100), nullable=False),
            sa.Column('display_name', sa.String(200), nullable=False),
            sa.Column('is_enabled', sa.Boolean, nullable=False, server_default='1'),
            sa.Column('model_type', sa.String(50), nullable=True),
            sa.Column('context_window', sa.Integer, nullable=True),
            sa.Column('max_output_tokens', sa.Integer, nullable=True),
            sa.Column('input_price', sa.Float, nullable=True),
            sa.Column('output_price', sa.Float, nullable=True),
            sa.Column('pricing_notes', sa.Text, nullable=True),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('tags', sa.Text, nullable=True),
            sa.Column('is_default', sa.Boolean, nullable=False, server_default='0'),
            sa.Column('priority', sa.Integer, nullable=False, server_default='0'),
            sa.Column('last_checked', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_available', sa.Boolean, nullable=False, server_default='1'),
            sa.Column('usage_count', sa.Integer, nullable=False, server_default='0'),
            sa.Column('total_input_tokens', sa.Integer, nullable=False, server_default='0'),
            sa.Column('total_output_tokens', sa.Integer, nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
    else:
        print("ai_model_configs table already exists, skipping creation")

    # Step 2: Create indexes if they don't exist
    indexes_to_create = [
        ('idx_model_provider_name', ['provider_name', 'model_name'], False),
        ('idx_model_enabled', ['is_enabled'], False),
        ('idx_model_default', ['provider_name', 'is_default'], False),
        ('idx_model_priority', ['provider_name', 'priority'], False),
        ('uix_provider_model', ['provider_name', 'model_name'], True),
    ]

    for index_name, columns, unique in indexes_to_create:
        if not index_exists(inspector, 'ai_model_configs', index_name):
            print(f"Creating index {index_name}...")
            try:
                op.create_index(
                    index_name,
                    'ai_model_configs',
                    columns,
                    unique=unique
                )
            except Exception as e:
                print(f"Warning: Could not create index {index_name}: {e}")
                # Continue with migration even if index creation fails
        else:
            print(f"Index {index_name} already exists, skipping")

    # Step 3: Create foreign key if it doesn't exist
    if not foreign_key_exists(inspector, 'ai_model_configs', 'fk_model_provider'):
        print("Creating foreign key constraint...")
        try:
            # Verify that ai_provider_configs table exists
            if table_exists(inspector, 'ai_provider_configs'):
                op.create_foreign_key(
                    'fk_model_provider',
                    'ai_model_configs',
                    'ai_provider_configs',
                    ['provider_name'],
                    ['provider_name'],
                    ondelete='CASCADE'
                )
            else:
                print("Warning: ai_provider_configs table doesn't exist, skipping foreign key creation")
        except Exception as e:
            print(f"Warning: Could not create foreign key: {e}")
    else:
        print("Foreign key fk_model_provider already exists, skipping")

    # Step 4: Insert default models (with duplicate handling)
    print("Inserting default model configurations...")

    # Check which models already exist
    existing_models = set()
    try:
        result = conn.execute(
            sa.text("SELECT provider_name, model_name FROM ai_model_configs")
        )
        existing_models = {(row[0], row[1]) for row in result}
    except Exception as e:
        print(f"Warning: Could not query existing models: {e}")

    default_models = [
        # OpenAI
        {
            'provider': 'openai',
            'model': 'gpt-4o',
            'display': 'GPT-4o',
            'type': 'chat',
            'context': 128000,
            'max_out': 16384,
            'in_price': 2.5,
            'out_price': 10.0,
            'desc': 'Latest GPT-4 Omni model with vision capabilities',
            'tags': '["fast", "multimodal", "latest"]',
            'default': True,
        },
        {
            'provider': 'openai',
            'model': 'gpt-4o-mini',
            'display': 'GPT-4o Mini',
            'type': 'chat',
            'context': 128000,
            'max_out': 16384,
            'in_price': 0.15,
            'out_price': 0.6,
            'desc': 'Affordable GPT-4 level intelligence',
            'tags': '["fast", "cheap", "recommended"]',
            'default': False,
        },
        {
            'provider': 'openai',
            'model': 'gpt-4-turbo',
            'display': 'GPT-4 Turbo',
            'type': 'chat',
            'context': 128000,
            'max_out': 4096,
            'in_price': 10.0,
            'out_price': 30.0,
            'desc': 'High-capability GPT-4 Turbo model',
            'tags': '["powerful", "expensive"]',
            'default': False,
        },
        # DeepSeek
        {
            'provider': 'deepseek',
            'model': 'deepseek-chat',
            'display': 'DeepSeek Chat',
            'type': 'chat',
            'context': 64000,
            'max_out': 4096,
            'in_price': 0.14,
            'out_price': 0.28,
            'desc': 'DeepSeek powerful chat model',
            'tags': '["cheap", "chinese", "recommended"]',
            'default': True,
        },
        {
            'provider': 'deepseek',
            'model': 'deepseek-reasoner',
            'display': 'DeepSeek Reasoner',
            'type': 'reasoning',
            'context': 64000,
            'max_out': 8192,
            'in_price': 0.55,
            'out_price': 2.19,
            'desc': 'Advanced reasoning model with CoT',
            'tags': '["reasoning", "powerful"]',
            'default': False,
        },
        # Claude
        {
            'provider': 'claude',
            'model': 'claude-3-5-sonnet-20241022',
            'display': 'Claude 3.5 Sonnet',
            'type': 'chat',
            'context': 200000,
            'max_out': 8192,
            'in_price': 3.0,
            'out_price': 15.0,
            'desc': 'Most intelligent Claude model',
            'tags': '["powerful", "latest", "recommended"]',
            'default': True,
        },
        {
            'provider': 'claude',
            'model': 'claude-3-5-haiku-20241022',
            'display': 'Claude 3.5 Haiku',
            'type': 'chat',
            'context': 200000,
            'max_out': 8192,
            'in_price': 0.8,
            'out_price': 4.0,
            'desc': 'Fast and affordable Claude model',
            'tags': '["fast", "cheap"]',
            'default': False,
        },
        # Gemini
        {
            'provider': 'gemini',
            'model': 'gemini-2.0-flash-exp',
            'display': 'Gemini 2.0 Flash',
            'type': 'chat',
            'context': 1000000,
            'max_out': 8192,
            'in_price': 0.0,
            'out_price': 0.0,
            'desc': 'Free experimental Gemini 2.0 model',
            'tags': '["free", "fast", "experimental"]',
            'default': True,
        },
        # Ollama (local)
        {
            'provider': 'ollama',
            'model': 'qwen2.5:7b-instruct',
            'display': 'Qwen 2.5 (7B)',
            'type': 'chat',
            'context': 32768,
            'max_out': 2048,
            'in_price': 0.0,
            'out_price': 0.0,
            'desc': 'Free local Qwen model, excellent for Chinese',
            'tags': '["free", "local", "chinese", "recommended"]',
            'default': True,
        },
    ]

    inserted_count = 0
    skipped_count = 0

    for model_data in default_models:
        provider = model_data['provider']
        model = model_data['model']

        # Skip if already exists
        if (provider, model) in existing_models:
            print(f"  - Skipping {provider}:{model} (already exists)")
            skipped_count += 1
            continue

        try:
            model_id = f"{provider}_{model.replace(':', '_').replace('-', '_')}"
            now = datetime.now(timezone.utc)

            # Use INSERT ... ON CONFLICT DO NOTHING for databases that support it
            # Otherwise, use standard INSERT
            dialect = conn.dialect.name

            if dialect == 'postgresql':
                # PostgreSQL: Use ON CONFLICT DO NOTHING
                conn.execute(
                    sa.text("""
                        INSERT INTO ai_model_configs
                        (id, provider_name, model_name, display_name, is_enabled, model_type,
                         context_window, max_output_tokens, input_price, output_price,
                         description, tags, is_default, priority, is_available, usage_count,
                         total_input_tokens, total_output_tokens, created_at, updated_at)
                        VALUES
                        (:id, :provider, :model, :display, 1, :type,
                         :context, :max_out, :in_price, :out_price,
                         :desc, :tags, :default, 0, 1, 0,
                         0, 0, :now, :now)
                        ON CONFLICT (provider_name, model_name) DO NOTHING
                    """),
                    {
                        'id': model_id,
                        'provider': provider,
                        'model': model,
                        'display': model_data['display'],
                        'type': model_data.get('type'),
                        'context': model_data.get('context'),
                        'max_out': model_data.get('max_out'),
                        'in_price': model_data.get('in_price'),
                        'out_price': model_data.get('out_price'),
                        'desc': model_data.get('desc'),
                        'tags': model_data.get('tags'),
                        'default': model_data.get('default', False),
                        'now': now,
                    }
                )
            elif dialect == 'mysql':
                # MySQL: Use INSERT IGNORE
                conn.execute(
                    sa.text("""
                        INSERT IGNORE INTO ai_model_configs
                        (id, provider_name, model_name, display_name, is_enabled, model_type,
                         context_window, max_output_tokens, input_price, output_price,
                         description, tags, is_default, priority, is_available, usage_count,
                         total_input_tokens, total_output_tokens, created_at, updated_at)
                        VALUES
                        (:id, :provider, :model, :display, 1, :type,
                         :context, :max_out, :in_price, :out_price,
                         :desc, :tags, :default, 0, 1, 0,
                         0, 0, :now, :now)
                    """),
                    {
                        'id': model_id,
                        'provider': provider,
                        'model': model,
                        'display': model_data['display'],
                        'type': model_data.get('type'),
                        'context': model_data.get('context'),
                        'max_out': model_data.get('max_out'),
                        'in_price': model_data.get('in_price'),
                        'out_price': model_data.get('out_price'),
                        'desc': model_data.get('desc'),
                        'tags': model_data.get('tags'),
                        'default': model_data.get('default', False),
                        'now': now,
                    }
                )
            else:
                # SQLite, SQL Server, and others: Standard INSERT
                conn.execute(
                    sa.text("""
                        INSERT INTO ai_model_configs
                        (id, provider_name, model_name, display_name, is_enabled, model_type,
                         context_window, max_output_tokens, input_price, output_price,
                         description, tags, is_default, priority, is_available, usage_count,
                         total_input_tokens, total_output_tokens, created_at, updated_at)
                        VALUES
                        (:id, :provider, :model, :display, 1, :type,
                         :context, :max_out, :in_price, :out_price,
                         :desc, :tags, :default, 0, 1, 0,
                         0, 0, :now, :now)
                    """),
                    {
                        'id': model_id,
                        'provider': provider,
                        'model': model,
                        'display': model_data['display'],
                        'type': model_data.get('type'),
                        'context': model_data.get('context'),
                        'max_out': model_data.get('max_out'),
                        'in_price': model_data.get('in_price'),
                        'out_price': model_data.get('out_price'),
                        'desc': model_data.get('desc'),
                        'tags': model_data.get('tags'),
                        'default': model_data.get('default', False),
                        'now': now,
                    }
                )

            print(f"  + Inserted {provider}:{model}")
            inserted_count += 1

        except Exception as e:
            print(f"  ! Warning: Could not insert {provider}:{model}: {e}")
            skipped_count += 1
            continue

    print(f"\nSummary: {inserted_count} models inserted, {skipped_count} skipped")
    print("Migration completed successfully!")


def downgrade() -> None:
    """Downgrade database schema."""
    conn = op.get_bind()
    inspector = inspect(conn)

    if table_exists(inspector, 'ai_model_configs'):
        print("Dropping ai_model_configs table...")

        # Try to drop foreign key first (if it exists)
        if foreign_key_exists(inspector, 'ai_model_configs', 'fk_model_provider'):
            try:
                op.drop_constraint('fk_model_provider', 'ai_model_configs', type_='foreignkey')
            except Exception as e:
                print(f"Warning: Could not drop foreign key: {e}")

        # Drop the table
        op.drop_table('ai_model_configs')
        print("Table dropped successfully")
    else:
        print("ai_model_configs table doesn't exist, nothing to drop")
