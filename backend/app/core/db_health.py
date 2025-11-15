"""
Database Health Check and Auto-Repair Service.

Automatically detects and fixes database schema inconsistencies.
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.logging import get_logger
from app.core.db import engine

logger = get_logger(__name__)


class DatabaseHealthChecker:
    """Database health checker and auto-repair service."""

    def __init__(self, session: Session):
        self.session = session
        self.inspector = inspect(engine)

    def check_health(self) -> Dict[str, Any]:
        """
        Run comprehensive database health check.

        Returns:
            dict: Health check results
        """
        logger.info("Starting database health check...")

        results = {
            "overall_status": "healthy",
            "checks": [],
            "repairs": [],
            "errors": [],
        }

        # Check 1: Required tables exist
        table_check = self._check_required_tables()
        results["checks"].append(table_check)
        if not table_check["passed"]:
            results["overall_status"] = "degraded"

        # Check 2: Required columns exist
        column_check = self._check_required_columns()
        results["checks"].append(column_check)
        if not column_check["passed"]:
            results["overall_status"] = "degraded"

        # Check 3: Required indexes exist
        index_check = self._check_required_indexes()
        results["checks"].append(index_check)
        if not index_check["passed"]:
            results["overall_status"] = "degraded"

        # Check 4: Data integrity
        integrity_check = self._check_data_integrity()
        results["checks"].append(integrity_check)
        if not integrity_check["passed"]:
            results["overall_status"] = "degraded"

        logger.info(f"Database health check completed: {results['overall_status']}")
        return results

    def auto_repair(self) -> Dict[str, Any]:
        """
        Attempt to automatically repair database issues.

        Returns:
            dict: Repair results
        """
        logger.info("Starting database auto-repair...")

        results = {
            "success": True,
            "repairs": [],
            "errors": [],
        }

        try:
            # Repair 1: Fix missing provider column in model_registry
            if self._repair_model_registry_provider():
                results["repairs"].append("Fixed model_registry.provider column")

            # Repair 2: Initialize missing AI providers
            if self._repair_missing_providers():
                results["repairs"].append("Initialized missing AI provider configs")

            # Repair 3: Fix orphaned usage logs
            if self._repair_orphaned_logs():
                results["repairs"].append("Cleaned up orphaned usage logs")

            logger.info(f"Auto-repair completed: {len(results['repairs'])} repairs made")

        except Exception as e:
            logger.error(f"Auto-repair failed: {e}")
            results["success"] = False
            results["errors"].append(str(e))

        return results

    def _check_required_tables(self) -> Dict[str, Any]:
        """Check if all required tables exist."""
        required_tables = [
            'ai_provider_configs',
            'ai_provider_quotas',
            'ai_provider_usage_logs',
            'model_registry',
            'translation_jobs',
            'users',
        ]

        existing_tables = self.inspector.get_table_names()
        missing_tables = [t for t in required_tables if t not in existing_tables]

        return {
            "name": "required_tables",
            "passed": len(missing_tables) == 0,
            "message": f"Missing tables: {missing_tables}" if missing_tables else "All required tables exist",
            "missing": missing_tables,
        }

    def _check_required_columns(self) -> Dict[str, Any]:
        """Check if required columns exist in tables."""
        required_columns = {
            'model_registry': ['provider', 'name', 'context_length', 'cost_input_per_1k'],
            'ai_provider_configs': ['provider_name', 'is_enabled', 'api_key'],
            'ai_provider_quotas': ['provider_name', 'daily_limit', 'monthly_limit'],
        }

        missing = {}
        for table, columns in required_columns.items():
            if table in self.inspector.get_table_names():
                existing_cols = {col['name'] for col in self.inspector.get_columns(table)}
                missing_cols = [c for c in columns if c not in existing_cols]
                if missing_cols:
                    missing[table] = missing_cols

        return {
            "name": "required_columns",
            "passed": len(missing) == 0,
            "message": f"Missing columns: {missing}" if missing else "All required columns exist",
            "missing": missing,
        }

    def _check_required_indexes(self) -> Dict[str, Any]:
        """Check if required indexes exist."""
        required_indexes = {
            'model_registry': ['idx_model_provider_status'],
            'ai_provider_configs': ['idx_provider_enabled', 'idx_provider_priority'],
            'ai_provider_usage_logs': ['idx_usage_date', 'idx_usage_cost'],
        }

        missing = {}
        for table, indexes in required_indexes.items():
            if table in self.inspector.get_table_names():
                existing_indexes = {idx['name'] for idx in self.inspector.get_indexes(table)}
                missing_indexes = [idx for idx in indexes if idx not in existing_indexes]
                if missing_indexes:
                    missing[table] = missing_indexes

        return {
            "name": "required_indexes",
            "passed": len(missing) == 0,
            "message": f"Missing indexes: {missing}" if missing else "All required indexes exist",
            "missing": missing,
        }

    def _check_data_integrity(self) -> Dict[str, Any]:
        """Check data integrity."""
        issues = []

        try:
            # Check for models without provider
            result = self.session.execute(
                sa.text("SELECT COUNT(*) FROM model_registry WHERE provider IS NULL OR provider = ''")
            ).scalar()

            if result > 0:
                issues.append(f"{result} models without provider")

            # Check for enabled providers without config
            result = self.session.execute(
                sa.text("""
                    SELECT COUNT(*) FROM ai_provider_configs
                    WHERE is_enabled = 1 AND (api_key IS NULL OR api_key = '')
                    AND provider_name != 'ollama'
                """)
            ).scalar()

            if result > 0:
                issues.append(f"{result} enabled providers without API key")

        except Exception as e:
            issues.append(f"Integrity check error: {str(e)}")

        return {
            "name": "data_integrity",
            "passed": len(issues) == 0,
            "message": f"Issues: {issues}" if issues else "Data integrity OK",
            "issues": issues,
        }

    def _repair_model_registry_provider(self) -> bool:
        """Fix missing provider column in model_registry."""
        try:
            # Update models without provider to 'ollama'
            result = self.session.execute(
                sa.text("UPDATE model_registry SET provider = 'ollama' WHERE provider IS NULL OR provider = ''")
            )
            self.session.commit()

            if result.rowcount > 0:
                logger.info(f"Fixed {result.rowcount} models without provider")
                return True

        except Exception as e:
            logger.error(f"Failed to repair model_registry.provider: {e}")
            self.session.rollback()

        return False

    def _repair_missing_providers(self) -> bool:
        """Initialize missing AI provider configs."""
        try:
            from app.core.init_ai_providers import init_ai_providers

            init_ai_providers(self.session)
            return True

        except Exception as e:
            logger.error(f"Failed to initialize providers: {e}")
            self.session.rollback()

        return False

    def _repair_orphaned_logs(self) -> bool:
        """Clean up orphaned usage logs."""
        try:
            # Delete logs for non-existent providers
            result = self.session.execute(
                sa.text("""
                    DELETE FROM ai_provider_usage_logs
                    WHERE provider_name NOT IN (
                        SELECT provider_name FROM ai_provider_configs
                    )
                """)
            )
            self.session.commit()

            if result.rowcount > 0:
                logger.info(f"Cleaned up {result.rowcount} orphaned usage logs")
                return True

        except Exception as e:
            logger.error(f"Failed to clean orphaned logs: {e}")
            self.session.rollback()

        return False


def check_and_repair_database(session: Session) -> Dict[str, Any]:
    """
    Convenience function to check and repair database.

    Args:
        session: Database session

    Returns:
        dict: Combined check and repair results
    """
    checker = DatabaseHealthChecker(session)

    # Run health check
    health_results = checker.check_health()

    # Auto-repair if needed
    if health_results["overall_status"] != "healthy":
        logger.warning("Database health check failed, attempting auto-repair...")
        repair_results = checker.auto_repair()

        # Run health check again
        health_results_after = checker.check_health()

        return {
            "initial_status": health_results["overall_status"],
            "final_status": health_results_after["overall_status"],
            "repairs": repair_results["repairs"],
            "errors": repair_results["errors"],
        }

    return {
        "initial_status": health_results["overall_status"],
        "final_status": health_results["overall_status"],
        "repairs": [],
        "errors": [],
    }
