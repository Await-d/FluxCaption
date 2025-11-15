"""
Model synchronization utility.

Syncs models from Ollama to the database registry.
"""

import asyncio
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.model_registry import ModelRegistry
from app.services.ollama_client import ollama_client

logger = get_logger(__name__)


async def sync_models_from_ollama(db: Session) -> None:
    """
    Sync models from Ollama to database registry.

    This ensures that all models available in Ollama are registered
    in the database, even if they were manually added.

    Args:
        db: Database session
    """
    try:
        # Get models from Ollama
        ollama_models = await ollama_client.list_models()
        logger.info(f"Found {len(ollama_models)} models in Ollama")

        # Get existing models from database
        existing_models = {model.name: model for model in db.query(ModelRegistry).all()}

        # Sync each Ollama model
        synced_count = 0
        for ollama_model in ollama_models:
            model_name = ollama_model.get("name")
            if not model_name:
                continue

            if model_name in existing_models:
                # Update existing model
                model = existing_models[model_name]
                model.status = "available"
                model.size_bytes = ollama_model.get("size", 0)
                model.last_checked = datetime.utcnow()

                # Update details if available
                details = ollama_model.get("details", {})
                if details:
                    model.family = details.get("family")
                    model.parameter_size = details.get("parameter_size")
                    model.quantization = details.get("quantization_level")

                logger.info(f"Updated model: {model_name}")
            else:
                # Add new model
                details = ollama_model.get("details", {})
                model = ModelRegistry(
                    name=model_name,
                    status="available",
                    size_bytes=ollama_model.get("size", 0),
                    family=details.get("family"),
                    parameter_size=details.get("parameter_size"),
                    quantization=details.get("quantization_level"),
                    is_default=False,  # Don't auto-set as default
                    last_checked=datetime.utcnow(),
                )
                db.add(model)
                logger.info(f"Added new model: {model_name}")

            synced_count += 1

        db.commit()
        logger.info(f"Successfully synced {synced_count} models from Ollama")

    except Exception as e:
        logger.error(f"Failed to sync models from Ollama: {e}", exc_info=True)
        db.rollback()
        raise


def sync_models_from_ollama_sync(db: Session) -> None:
    """
    Synchronous wrapper for sync_models_from_ollama.

    Args:
        db: Database session
    """
    asyncio.run(sync_models_from_ollama(db))
