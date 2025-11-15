"""
AI Model Configuration Management Endpoints.

Provides API for managing AI model configurations and pricing.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.api.routers.auth import get_current_user
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.ai_model_config import AIModelConfig
from app.models.user import User
from app.schemas.ai_models import (
    AIModelConfigCreate,
    AIModelConfigList,
    AIModelConfigResponse,
    AIModelConfigUpdate,
    PricingCalculation,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ai-models", tags=["AI Models"])


@router.get(
    "",
    response_model=AIModelConfigList,
    summary="List AI model configurations",
)
async def list_models(
    current_user: Annotated[User, Depends(get_current_user)],
    provider: str | None = Query(None, description="Filter by provider"),
    enabled_only: bool = Query(False, description="Only return enabled models"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> AIModelConfigList:
    """
    List all AI model configurations with optional filtering.

    Args:
        provider: Filter by provider name
        enabled_only: Only return enabled models
        page: Page number (1-indexed)
        page_size: Number of items per page
        db: Database session

    Returns:
        AIModelConfigList: Paginated list of model configurations
    """
    # Build query
    query = db.query(AIModelConfig)

    if provider:
        query = query.filter(AIModelConfig.provider_name == provider)

    if enabled_only:
        query = query.filter(AIModelConfig.is_enabled)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    models = (
        query.order_by(
            desc(AIModelConfig.provider_name),
            desc(AIModelConfig.priority),
            AIModelConfig.display_name,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Convert to response models
    model_responses = [
        AIModelConfigResponse(
            id=str(model.id),
            provider_name=model.provider_name,
            model_name=model.model_name,
            display_name=model.display_name,
            is_enabled=model.is_enabled,
            model_type=model.model_type,
            context_window=model.context_window,
            max_output_tokens=model.max_output_tokens,
            input_price=model.input_price,
            output_price=model.output_price,
            pricing_notes=model.pricing_notes,
            description=model.description,
            tags=model.tags,
            is_default=model.is_default,
            priority=model.priority,
            is_available=model.is_available,
            usage_count=model.usage_count,
            total_input_tokens=model.total_input_tokens,
            total_output_tokens=model.total_output_tokens,
            last_checked=model.last_checked,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        for model in models
    ]

    return AIModelConfigList(
        models=model_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{model_id}",
    response_model=AIModelConfigResponse,
    summary="Get AI model configuration",
)
async def get_model(
    model_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> AIModelConfigResponse:
    """
    Get detailed model configuration.

    Args:
        model_id: Model configuration ID
        db: Database session

    Returns:
        AIModelConfigResponse: Model configuration

    Raises:
        HTTPException: If model not found
    """
    model = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model configuration '{model_id}' not found",
        )

    return AIModelConfigResponse(
        id=str(model.id),
        provider_name=model.provider_name,
        model_name=model.model_name,
        display_name=model.display_name,
        is_enabled=model.is_enabled,
        model_type=model.model_type,
        context_window=model.context_window,
        max_output_tokens=model.max_output_tokens,
        input_price=model.input_price,
        output_price=model.output_price,
        pricing_notes=model.pricing_notes,
        description=model.description,
        tags=model.tags,
        is_default=model.is_default,
        priority=model.priority,
        is_available=model.is_available,
        usage_count=model.usage_count,
        total_input_tokens=model.total_input_tokens,
        total_output_tokens=model.total_output_tokens,
        last_checked=model.last_checked,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post(
    "",
    response_model=AIModelConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create AI model configuration",
)
async def create_model(
    request: AIModelConfigCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> AIModelConfigResponse:
    """
    Create a new AI model configuration.

    Args:
        request: Model configuration data
        db: Database session

    Returns:
        AIModelConfigResponse: Created model configuration

    Raises:
        HTTPException: If model already exists or creation fails
    """
    try:
        # Check if model already exists
        existing = (
            db.query(AIModelConfig)
            .filter(
                and_(
                    AIModelConfig.provider_name == request.provider_name,
                    AIModelConfig.model_name == request.model_name,
                )
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Model '{request.model_name}' already exists for provider '{request.provider_name}'",
            )

        # If this is set as default, unset other defaults for this provider
        if request.is_default:
            db.query(AIModelConfig).filter(
                AIModelConfig.provider_name == request.provider_name
            ).update({"is_default": False})

        # Create model configuration
        model = AIModelConfig(
            provider_name=request.provider_name,
            model_name=request.model_name,
            display_name=request.display_name,
            is_enabled=request.is_enabled,
            model_type=request.model_type,
            context_window=request.context_window,
            max_output_tokens=request.max_output_tokens,
            input_price=request.input_price,
            output_price=request.output_price,
            pricing_notes=request.pricing_notes,
            description=request.description,
            tags=request.tags,
            is_default=request.is_default,
            priority=request.priority,
        )

        db.add(model)
        db.commit()
        db.refresh(model)

        logger.info(f"Created model configuration: {model.provider_name}:{model.model_name}")

        return AIModelConfigResponse.model_validate(model)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create model configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create model configuration: {str(e)}",
        )


@router.patch(
    "/{model_id}",
    response_model=AIModelConfigResponse,
    summary="Update AI model configuration",
)
async def update_model(
    model_id: str,
    request: AIModelConfigUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> AIModelConfigResponse:
    """
    Update an AI model configuration.

    Args:
        model_id: Model configuration ID
        request: Update data
        db: Database session

    Returns:
        AIModelConfigResponse: Updated model configuration

    Raises:
        HTTPException: If model not found or update fails
    """
    model = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model configuration '{model_id}' not found",
        )

    try:
        # If setting as default, unset other defaults for this provider
        if request.is_default:
            db.query(AIModelConfig).filter(
                and_(
                    AIModelConfig.provider_name == model.provider_name,
                    AIModelConfig.id != model_id,
                )
            ).update({"is_default": False})

        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(model, field, value)

        db.commit()
        db.refresh(model)

        logger.info(f"Updated model configuration: {model.provider_name}:{model.model_name}")

        return AIModelConfigResponse.model_validate(model)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update model configuration {model_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update model configuration: {str(e)}",
        )


@router.delete(
    "/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete AI model configuration",
)
async def delete_model(
    model_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> None:
    """
    Delete an AI model configuration.

    Args:
        model_id: Model configuration ID
        db: Database session

    Raises:
        HTTPException: If model not found or deletion fails
    """
    model = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model configuration '{model_id}' not found",
        )

    try:
        db.delete(model)
        db.commit()

        logger.info(f"Deleted model configuration: {model.provider_name}:{model.model_name}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete model configuration {model_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model configuration: {str(e)}",
        )


@router.post(
    "/calculate-price",
    response_model=PricingCalculation,
    summary="Calculate pricing for token usage",
)
async def calculate_price(
    provider_name: str = Query(..., description="Provider name"),
    model_name: str = Query(..., description="Model name"),
    input_tokens: int = Query(..., ge=0, description="Number of input tokens"),
    output_tokens: int = Query(..., ge=0, description="Number of output tokens"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
) -> PricingCalculation:
    """
    Calculate the cost for given token usage.

    Args:
        provider_name: Provider name
        model_name: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        db: Database session

    Returns:
        PricingCalculation: Cost breakdown

    Raises:
        HTTPException: If model not found or pricing not available
    """
    model = (
        db.query(AIModelConfig)
        .filter(
            and_(
                AIModelConfig.provider_name == provider_name,
                AIModelConfig.model_name == model_name,
            )
        )
        .first()
    )

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found for provider '{provider_name}'",
        )

    if model.input_price is None or model.output_price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pricing information not available for model '{model_name}'",
        )

    total_cost = model.calculate_cost(input_tokens, output_tokens)
    input_cost = (input_tokens / 1_000_000) * model.input_price
    output_cost = (output_tokens / 1_000_000) * model.output_price

    return PricingCalculation(
        model_name=model_name,
        provider_name=provider_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost,
    )
