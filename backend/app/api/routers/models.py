"""
Model management endpoints.

Provides API for managing Ollama models.
"""

from typing import Annotated
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.api.routers.auth import get_current_user
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
async def list_models(
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
async def get_model(
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

        # Get model info from Ollama to update size and details
        ollama_models = await ollama_client.list_models()
        ollama_model = next(
            (m for m in ollama_models if m.get("name") == model_name),
            None
        )

        # Update status to available and populate size info
        if model:
            model.status = "available"
            if ollama_model:
                model.size_bytes = ollama_model.get("size")
                details = ollama_model.get("details", {})
                if details:
                    model.family = details.get("family")
                    model.parameter_size = details.get("parameter_size")
                    model.quantization = details.get("quantization_level")
                model.digest = ollama_model.get("digest")
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
    current_user: Annotated[User, Depends(get_current_user)],
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



@router.post(
    "/{model_name}/test",
    summary="Test a model",
)
async def test_model(
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
        dict: Test result with response time and output

    Raises:
        HTTPException: If test fails
    """
    import time
    
    try:
        # Check if model exists in Ollama
        models = await ollama_client.list_models()
        if not any(m.get("name") == model_name for m in models):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_name}' not found in Ollama",
            )

        # Run test generation
        test_prompt = "Translate to English: 你好"
        start_time = time.time()
        
        response = await ollama_client.generate(
            model=model_name,
            prompt=test_prompt,
            system="You are a translation assistant. Respond with only the translation.",
            temperature=0.3,
            max_tokens=50,
        )
        
        elapsed_time = time.time() - start_time

        # Update model registry
        model = db.query(ModelRegistry).filter(ModelRegistry.name == model_name).first()
        if model:
            model.status = "available"
            model.last_checked = model.last_checked  # Will be updated by DB trigger
            db.commit()

        logger.info(f"Successfully tested model {model_name} in {elapsed_time:.2f}s")

        return {
            "success": True,
            "model": model_name,
            "test_prompt": test_prompt,
            "response": response.strip(),
            "response_time_seconds": round(elapsed_time, 2),
            "status": "available",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test model {model_name}: {e}", exc_info=True)
        
        # Update model status to error
        model = db.query(ModelRegistry).filter(ModelRegistry.name == model_name).first()
        if model:
            model.status = "error"
            db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test model: {str(e)}",
        )



@router.post(
    "/{model_name}/set-default",
    summary="Set model as default",
)
async def set_default_model(
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
        model = db.query(ModelRegistry).filter(ModelRegistry.name == model_name).first()
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
        db.query(ModelRegistry).update({"is_default": False})

        # Set this model as default
        model.is_default = True
        db.commit()

        # Update database setting
        from app.models.setting import Setting
        default_model_setting = db.query(Setting).filter(
            Setting.key == "default_mt_model"
        ).first()

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
async def get_recommended_models(
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
    summary="Sync models from Ollama",
)
async def sync_models(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict:
    """
    Sync models from Ollama server to local database.

    This will fetch all models from Ollama and update the local registry.

    Returns:
        dict: Sync result with counts
    """
    try:
        from app.core.model_sync import sync_models_from_ollama

        logger.info("Starting manual model sync from Ollama")
        await sync_models_from_ollama(db)

        # Get updated model count
        model_count = db.query(ModelRegistry).count()

        logger.info(f"Model sync completed, total models: {model_count}")

        return {
            "success": True,
            "message": "Models synced successfully",
            "total_models": model_count,
        }

    except Exception as e:
        logger.error(f"Failed to sync models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync models: {str(e)}",
        )
