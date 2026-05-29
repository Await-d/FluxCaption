"""
Model management endpoints.

Provides API for managing Ollama models.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.routers.auth import get_current_user
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.model_registry import ModelRegistry
from app.models.user import User
from app.schemas.models import (
    ModelDeleteResponse,
    ModelInfo,
    ModelListResponse,
    ModelPullRequest,
)
from app.services.ollama_client import ollama_client
from app.workers.tasks import pull_model_task, sync_models_task, test_model_task

logger = get_logger(__name__)

router = APIRouter(prefix="/api/models", tags=["Models"])
OLLAMA_PROVIDER = "ollama"


def _delete_model_registry_entry(db: Session, model_name: str) -> None:
    model = (
        db.query(ModelRegistry)
        .filter(ModelRegistry.provider == OLLAMA_PROVIDER, ModelRegistry.name == model_name)
        .first()
    )
    if model:
        db.delete(model)
        db.commit()


@router.get(
    "",
    response_model=ModelListResponse,
    summary="List all models",
)
def list_models(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> ModelListResponse:
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
def get_model(
    model_name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> ModelInfo:
    """
    Get detailed information about a specific model.

    Args:
        model_name: Name of the model

    Returns:
        ModelInfo: Model information

    Raises:
        HTTPException: If model not found
    """
    model = (
        db.query(ModelRegistry)
        .filter(ModelRegistry.provider == OLLAMA_PROVIDER, ModelRegistry.name == model_name)
        .first()
    )

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


@router.post(
    "/pull",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pull a model",
)
def pull_model(
    request: ModelPullRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict:
    """
    Pull a model from Ollama registry.

    This operation runs in the background. Check the model status
    to see when the pull is complete.

    Args:
        request: Model pull request
        db: Database session

    Returns:
        dict: Status message
    """
    try:
        # Check if model already exists
        existing_model = (
            db.query(ModelRegistry)
            .filter(ModelRegistry.provider == OLLAMA_PROVIDER, ModelRegistry.name == request.name)
            .first()
        )

        if existing_model and existing_model.status == "pulling":
            return {
                "message": f"Model '{request.name}' is already being pulled",
                "status": "pulling",
            }

        # Create or update model registry entry
        if not existing_model:
            model = ModelRegistry(provider=OLLAMA_PROVIDER, name=request.name, status="pulling")
            db.add(model)
        else:
            existing_model.status = "pulling"
            existing_model.error_message = None

        db.commit()

        task = pull_model_task.apply_async(args=[request.name], queue="models")

        return {
            "message": f"Started pulling model '{request.name}'",
            "status": "pulling",
            "task_id": task.id,
            "model": request.name,
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
    current_user: Annotated[User, Depends(get_current_user)],
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

        await run_in_threadpool(_delete_model_registry_entry, db, model_name)

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


@router.post(
    "/{model_name}/test",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Test a model",
)
def test_model(
    model_name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict:
    """
    Test a model by running a simple generation task.

    Args:
        model_name: Name of the model to test
        db: Database session

    Returns:
        dict: Queued task details

    Raises:
        HTTPException: If test fails
    """
    try:
        model = (
            db.query(ModelRegistry)
            .filter(ModelRegistry.provider == OLLAMA_PROVIDER, ModelRegistry.name == model_name)
            .first()
        )
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_name}' not found in registry",
            )

        task = test_model_task.apply_async(args=[model_name], queue="models")

        return {
            "status": "queued",
            "task_id": task.id,
            "model": model_name,
            "message": f"Model test queued for '{model_name}'",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test model {model_name}: {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test model: {str(e)}",
        )


@router.post(
    "/{model_name}/set-default",
    summary="Set model as default",
)
def set_default_model(
    model_name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict:
    """
    Set a model as the default translation model.

    Args:
        model_name: Name of the model to set as default
        db: Database session

    Returns:
        dict: Success message

    Raises:
        HTTPException: If model not found
    """
    try:
        # Check if model exists in registry
        model = (
            db.query(ModelRegistry)
            .filter(ModelRegistry.provider == OLLAMA_PROVIDER, ModelRegistry.name == model_name)
            .first()
        )
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_name}' not found in registry",
            )

        # Check if model is available
        if model.status != "available":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{model_name}' is not available (status: {model.status})",
            )

        # Unset all other defaults
        db.query(ModelRegistry).filter(ModelRegistry.provider == OLLAMA_PROVIDER).update(
            {"is_default": False}
        )

        # Set this model as default
        model.is_default = True
        db.commit()

        # Update database setting
        from app.models.setting import Setting

        default_model_setting = db.query(Setting).filter(Setting.key == "default_mt_model").first()

        if default_model_setting:
            default_model_setting.value = model_name
        else:
            default_model_setting = Setting(
                key="default_mt_model",
                value=model_name,
                value_type="string",
            )
            db.add(default_model_setting)

        db.commit()

        # Update runtime settings instance
        from app.core.config import settings

        settings.default_mt_model = model_name

        logger.info(f"Set default model to: {model_name} (updated both DB and runtime config)")

        return {
            "success": True,
            "message": f"Model '{model_name}' set as default",
            "default_model": model_name,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set default model: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set default model: {str(e)}",
        )


@router.get(
    "/recommended/list",
    summary="Get recommended models",
)
def get_recommended_models(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Get a list of recommended models for translation tasks.

    Returns:
        dict: List of recommended models with descriptions
    """
    recommended = [
        {
            "name": "qwen2.5:0.5b-instruct",
            "display_name": "Qwen2.5 0.5B",
            "description": "超轻量级模型，内存占用极低（~400MB），适合内存受限环境",
            "size_estimate": "397 MB",
            "performance": "fast",
            "quality": "basic",
            "recommended_for": "低配置设备",
        },
        {
            "name": "qwen2.5:1.5b-instruct",
            "display_name": "Qwen2.5 1.5B",
            "description": "轻量级模型，平衡性能和质量（~1GB）",
            "size_estimate": "1.0 GB",
            "performance": "fast",
            "quality": "good",
            "recommended_for": "日常使用",
        },
        {
            "name": "qwen2.5:3b-instruct",
            "display_name": "Qwen2.5 3B",
            "description": "中型模型，提供更好的翻译质量（~2GB）",
            "size_estimate": "2.0 GB",
            "performance": "medium",
            "quality": "very good",
            "recommended_for": "推荐使用",
        },
        {
            "name": "qwen2.5:7b-instruct",
            "display_name": "Qwen2.5 7B (默认)",
            "description": "默认推荐模型，高质量翻译（~5GB）",
            "size_estimate": "4.7 GB",
            "performance": "medium",
            "quality": "excellent",
            "recommended_for": "高质量翻译",
        },
        {
            "name": "gemma2:2b-instruct",
            "display_name": "Gemma2 2B",
            "description": "Google Gemma2，轻量高效（~1.6GB）",
            "size_estimate": "1.6 GB",
            "performance": "fast",
            "quality": "good",
            "recommended_for": "快速翻译",
        },
        {
            "name": "llama3.2:3b-instruct",
            "display_name": "Llama 3.2 3B",
            "description": "Meta Llama3.2，通用性强（~2GB）",
            "size_estimate": "2.0 GB",
            "performance": "medium",
            "quality": "very good",
            "recommended_for": "通用场景",
        },
    ]

    return {
        "recommended_models": recommended,
        "total": len(recommended),
    }


@router.post(
    "/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sync models from Ollama",
)
def sync_models(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Sync models from Ollama server to local database.

    This will fetch all models from Ollama and update the local registry.

    Returns:
        dict: Queued task details
    """
    try:
        logger.info("Queueing manual model sync from Ollama")
        task = sync_models_task.apply_async(queue="models")

        return {
            "status": "queued",
            "task_id": task.id,
            "message": "Model sync queued",
        }

    except Exception as e:
        logger.error(f"Failed to sync models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync models: {str(e)}",
        )
