"""
Model management endpoints.

Provides API for managing Ollama models.
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.ollama_client import ollama_client
from app.models.model_registry import ModelRegistry
from app.schemas.models import (
    ModelInfo,
    ModelPullRequest,
    ModelDeleteResponse,
    ModelListResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/models", tags=["Models"])


@router.get(
    "",
    response_model=ModelListResponse,
    summary="List all models",
)
async def list_models(db: Session = Depends(get_db)) -> ModelListResponse:
    """
    List all tracked models.

    Returns:
        ModelListResponse: List of all models in the registry
    """
    try:
        models = db.query(ModelRegistry).all()
        model_infos = [
            ModelInfo(
                name=model.name,
                status=model.status,
                size_bytes=model.size_bytes,
                family=model.family,
                parameter_size=model.parameter_size,
                quantization=model.quantization,
                last_checked=model.last_checked,
                last_used=model.last_used,
                usage_count=model.usage_count,
                is_default=model.is_default,
            )
            for model in models
        ]

        return ModelListResponse(models=model_infos, total=len(model_infos))

    except Exception as e:
        logger.error(f"Failed to list models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}",
        )


@router.get(
    "/{model_name}",
    response_model=ModelInfo,
    summary="Get model information",
)
async def get_model(model_name: str, db: Session = Depends(get_db)) -> ModelInfo:
    """
    Get detailed information about a specific model.

    Args:
        model_name: Name of the model

    Returns:
        ModelInfo: Model information

    Raises:
        HTTPException: If model not found
    """
    model = db.query(ModelRegistry).filter(ModelRegistry.name == model_name).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found",
        )

    return ModelInfo(
        name=model.name,
        status=model.status,
        size_bytes=model.size_bytes,
        family=model.family,
        parameter_size=model.parameter_size,
        quantization=model.quantization,
        last_checked=model.last_checked,
        last_used=model.last_used,
        usage_count=model.usage_count,
        is_default=model.is_default,
    )


async def pull_model_task(model_name: str, db: Session) -> None:
    """
    Background task to pull a model.

    Args:
        model_name: Name of the model to pull
        db: Database session
    """
    try:
        # Update status to pulling
        model = db.query(ModelRegistry).filter(ModelRegistry.name == model_name).first()
        if model:
            model.status = "pulling"
            db.commit()

        # Pull the model
        await ollama_client.pull_model(model_name)

        # Update status to available
        if model:
            model.status = "available"
            db.commit()

        logger.info(f"Successfully pulled model: {model_name}")

    except Exception as e:
        logger.error(f"Failed to pull model {model_name}: {e}", exc_info=True)

        # Update status to failed
        model = db.query(ModelRegistry).filter(ModelRegistry.name == model_name).first()
        if model:
            model.status = "failed"
            model.error_message = str(e)
            db.commit()


@router.post(
    "/pull",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pull a model",
)
async def pull_model(
    request: ModelPullRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """
    Pull a model from Ollama registry.

    This operation runs in the background. Check the model status
    to see when the pull is complete.

    Args:
        request: Model pull request
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        dict: Status message
    """
    try:
        # Check if model already exists
        existing_model = db.query(ModelRegistry).filter(
            ModelRegistry.name == request.name
        ).first()

        if existing_model and existing_model.status == "pulling":
            return {
                "message": f"Model '{request.name}' is already being pulled",
                "status": "pulling",
            }

        # Create or update model registry entry
        if not existing_model:
            model = ModelRegistry(name=request.name, status="pulling")
            db.add(model)
        else:
            existing_model.status = "pulling"

        db.commit()

        # Start background task
        background_tasks.add_task(pull_model_task, request.name, db)

        return {
            "message": f"Started pulling model '{request.name}'",
            "status": "pulling",
        }

    except Exception as e:
        logger.error(f"Failed to initiate model pull: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pull model: {str(e)}",
        )


@router.delete(
    "/{model_name}",
    response_model=ModelDeleteResponse,
    summary="Delete a model",
)
async def delete_model(
    model_name: str,
    db: Session = Depends(get_db),
) -> ModelDeleteResponse:
    """
    Delete a model from Ollama and the registry.

    Args:
        model_name: Name of the model to delete
        db: Database session

    Returns:
        ModelDeleteResponse: Deletion result

    Raises:
        HTTPException: If deletion fails
    """
    try:
        # Delete from Ollama
        await ollama_client.delete_model(model_name)

        # Delete from registry
        model = db.query(ModelRegistry).filter(ModelRegistry.name == model_name).first()
        if model:
            db.delete(model)
            db.commit()

        logger.info(f"Successfully deleted model: {model_name}")

        return ModelDeleteResponse(
            success=True,
            message=f"Model '{model_name}' deleted successfully",
        )

    except Exception as e:
        logger.error(f"Failed to delete model {model_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model: {str(e)}",
        )
