#!/usr/bin/env python3
"""
Database migration script.

Runs Alembic migrations programmatically without requiring the alembic command.
"""

import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from alembic import command
from alembic.config import Config


def run_migrations():
    """Run database migrations to latest version."""
    
    print("=" * 80)
    print("FluxCaption Database Migration")
    print("=" * 80)
    
    # Get alembic.ini path
    alembic_cfg_path = backend_dir / "alembic.ini"
    
    if not alembic_cfg_path.exists():
        print(f"❌ Error: alembic.ini not found at {alembic_cfg_path}")
        sys.exit(1)
    
    print(f"\n📁 Using config: {alembic_cfg_path}")
    
    # Create Alembic config
    alembic_cfg = Config(str(alembic_cfg_path))
    
    # Set the script location (migrations directory)
    migrations_dir = backend_dir / "migrations"
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    
    print(f"📁 Migrations directory: {migrations_dir}")
    
    try:
        # Show current version
        print("\n" + "=" * 80)
        print("Current Database Version")
        print("=" * 80)
        command.current(alembic_cfg, verbose=True)
        
        # Run upgrade to head
        print("\n" + "=" * 80)
        print("Running Migrations")
        print("=" * 80)
        print("\n⏳ Upgrading to latest version...")
        
        command.upgrade(alembic_cfg, "head")
        
        print("\n✅ Migration completed successfully!")
        
        # Show new version
        print("\n" + "=" * 80)
        print("New Database Version")
        print("=" * 80)
        command.current(alembic_cfg, verbose=True)
        
        print("\n" + "=" * 80)
        print("✅ All migrations applied successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()

