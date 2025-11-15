"""
AI Provider Configuration API Router.

Endpoints for managing AI provider configurations, quotas, and usage monitoring.
"""

from datetime import datetime, timedelta

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.logging import get_logger
from app.models.ai_provider_config import AIProviderConfig
from app.models.ai_provider_usage import AIProviderUsageLog
from app.services.ai_providers.factory import AIProviderFactory, provider_manager
from app.services.ai_quota_service import AIQuotaService

logger = get_logger(__name__)
router = APIRouter(prefix="/ai-providers", tags=["AI Providers"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class ProviderConfigCreate(BaseModel):
    """Schema for creating/updating provider config."""

    provider_name: str = Field(..., description="Provider identifier (e.g., 'openai', 'deepseek')")
    display_name: str = Field(..., description="Display name for UI")
    is_enabled: bool = Field(default=False, description="Whether provider is enabled")
    api_key: str | None = Field(default=None, description="API key (encrypted)")
    base_url: str | None = Field(default=None, description="API base URL")
    timeout: int = Field(default=300, description="Request timeout in seconds")
    extra_config: dict | None = Field(default=None, description="Extra configuration as JSON")
    default_model: str | None = Field(default=None, description="Default model name")
    priority: int = Field(default=0, description="Display priority (higher = first)")
    description: str | None = Field(default=None, description="Provider description")


class ProviderConfigResponse(BaseModel):
    """Schema for provider config response."""

    id: str
    provider_name: str
    display_name: str
    is_enabled: bool
    base_url: str | None
    timeout: int
    default_model: str | None
    last_health_check: datetime | None
    is_healthy: bool
    health_error: str | None
    priority: int
    description: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuotaConfigUpdate(BaseModel):
    """Schema for updating quota configuration."""

    daily_limit: float | None = Field(default=None, description="Daily spending limit in USD")
    monthly_limit: float | None = Field(default=None, description="Monthly spending limit in USD")
    daily_token_limit: int | None = Field(default=None, description="Daily token limit")
    monthly_token_limit: int | None = Field(default=None, description="Monthly token limit")
    requests_per_minute: int | None = Field(default=None, description="Max requests per minute")
    requests_per_hour: int | None = Field(default=None, description="Max requests per hour")
    alert_threshold_percent: int = Field(default=80, description="Alert threshold percentage")
    auto_disable_on_limit: bool = Field(
        default=True, description="Auto-disable when limit exceeded"
    )


class QuotaResponse(BaseModel):
    """Schema for quota response."""

    provider_name: str
    daily_limit: float | None
    monthly_limit: float | None
    current_daily_cost: float
    current_monthly_cost: float
    current_daily_tokens: int
    current_monthly_tokens: int
    daily_remaining: float | None
    monthly_remaining: float | None
    daily_usage_percent: float
    monthly_usage_percent: float
    alert_threshold_percent: int
    auto_disable_on_limit: bool
    daily_reset_at: datetime | None
    monthly_reset_at: datetime | None

    class Config:
        from_attributes = True


class UsageStatsResponse(BaseModel):
    """Schema for usage statistics response."""

    provider: str
    request_count: int
    total_tokens: int
    total_cost: float
    avg_response_time_ms: float
    error_count: int
    success_rate: float


# =============================================================================
# Provider Configuration Endpoints
# =============================================================================


@router.get("", response_model=list[ProviderConfigResponse])
async def list_providers(
    enabled_only: bool = Query(default=False, description="Only return enabled providers"),
    db: Session = Depends(get_db),
):
    """List all AI provider configurations."""
    stmt = sa.select(AIProviderConfig)

    if enabled_only:
        stmt = stmt.where(AIProviderConfig.is_enabled)

    stmt = stmt.order_by(AIProviderConfig.priority.desc(), AIProviderConfig.created_at)

    providers = db.execute(stmt).scalars().all()
    return providers


@router.get("/{provider_name}", response_model=ProviderConfigResponse)
async def get_provider(
    provider_name: str,
    db: Session = Depends(get_db),
):
    """Get a specific provider configuration."""
    stmt = sa.select(AIProviderConfig).where(AIProviderConfig.provider_name == provider_name)
    provider = db.execute(stmt).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

    return provider


@router.post("", response_model=ProviderConfigResponse)
async def create_or_update_provider(
    config: ProviderConfigCreate,
    db: Session = Depends(get_db),
):
    """Create or update a provider configuration."""

    # Check if provider name is valid
    available_providers = AIProviderFactory.get_available_providers()
    if config.provider_name not in available_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider '{config.provider_name}'. "
            f"Available: {', '.join(available_providers)}",
        )

    # Check if exists
    stmt = sa.select(AIProviderConfig).where(AIProviderConfig.provider_name == config.provider_name)
    existing = db.execute(stmt).scalar_one_or_none()

    if existing:
        # Update existing
        for field, value in config.model_dump(exclude_unset=True).items():
            if field == "extra_config" and value is not None:
                import json

                setattr(existing, field, json.dumps(value))
            else:
                setattr(existing, field, value)

        db.commit()
        db.refresh(existing)
        logger.info(f"Updated provider config: {config.provider_name}")
        return existing
    else:
        # Create new
        import json

        provider_config = AIProviderConfig(
            **config.model_dump(exclude={"extra_config"}),
            extra_config=json.dumps(config.extra_config) if config.extra_config else None,
        )
        db.add(provider_config)
        db.commit()
        db.refresh(provider_config)
        logger.info(f"Created provider config: {config.provider_name}")
        return provider_config


@router.delete("/{provider_name}")
async def delete_provider(
    provider_name: str,
    db: Session = Depends(get_db),
):
    """Delete a provider configuration."""
    stmt = sa.select(AIProviderConfig).where(AIProviderConfig.provider_name == provider_name)
    provider = db.execute(stmt).scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

    db.delete(provider)
    db.commit()
    logger.info(f"Deleted provider config: {provider_name}")

    return {"message": f"Provider '{provider_name}' deleted successfully"}


@router.post("/{provider_name}/health-check")
async def check_provider_health(
    provider_name: str,
    db: Session = Depends(get_db),
):
    """Check provider health and update status."""

    # Get provider config
    stmt = sa.select(AIProviderConfig).where(AIProviderConfig.provider_name == provider_name)
    config_record = db.execute(stmt).scalar_one_or_none()

    if not config_record:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

    try:
        # Get provider instance
        import json

        provider_config = {
            "api_key": config_record.api_key,
            "base_url": config_record.base_url,
            "timeout": config_record.timeout,
        }

        if config_record.extra_config:
            try:
                extra = json.loads(config_record.extra_config)
                provider_config.update(extra)
            except:
                pass

        provider = provider_manager.get_provider(
            provider_name,
            config=provider_config,
            use_cache=False,  # Don't use cache for health check
        )

        # Perform health check
        is_healthy = await provider.health_check()

        # Update database
        config_record.is_healthy = is_healthy
        config_record.last_health_check = datetime.now()
        config_record.health_error = None if is_healthy else "Health check failed"

        db.commit()

        return {
            "provider": provider_name,
            "is_healthy": is_healthy,
            "checked_at": config_record.last_health_check,
        }

    except Exception as e:
        # Update error status
        config_record.is_healthy = False
        config_record.last_health_check = datetime.now()
        config_record.health_error = str(e)[:500]
        db.commit()

        logger.error(f"Health check failed for {provider_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/{provider_name}/models")
async def list_provider_models(
    provider_name: str,
    db: Session = Depends(get_db),
):
    """List available models for a provider."""

    # Get provider config
    stmt = sa.select(AIProviderConfig).where(AIProviderConfig.provider_name == provider_name)
    config_record = db.execute(stmt).scalar_one_or_none()

    if not config_record:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

    try:
        # Get provider instance
        import json

        provider_config = {
            "api_key": config_record.api_key,
            "base_url": config_record.base_url,
            "timeout": config_record.timeout,
        }

        if config_record.extra_config:
            try:
                extra = json.loads(config_record.extra_config)
                provider_config.update(extra)
            except:
                pass

        provider = provider_manager.get_provider(
            provider_name, config=provider_config, use_cache=False
        )

        # List models
        models = await provider.list_models()

        return {
            "provider": provider_name,
            "models": [
                {
                    "id": model.id,
                    "name": model.name,
                    "context_length": model.context_length,
                    "supports_streaming": model.supports_streaming,
                    "cost_per_1k_input": model.cost_per_1k_input_tokens,
                    "cost_per_1k_output": model.cost_per_1k_output_tokens,
                    "description": model.description,
                }
                for model in models
            ],
            "count": len(models),
        }

    except Exception as e:
        logger.error(f"Failed to list models for {provider_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


# =============================================================================
# Quota Management Endpoints
# =============================================================================


@router.get("/{provider_name}/quota", response_model=QuotaResponse)
async def get_provider_quota(
    provider_name: str,
    db: Session = Depends(get_db),
):
    """Get quota configuration and current usage for a provider."""
    quota_service = AIQuotaService(db)
    quota = quota_service._get_or_create_quota(provider_name)

    # Reset if needed
    quota_service._reset_quota_if_needed(quota)

    return QuotaResponse(
        provider_name=quota.provider_name,
        daily_limit=quota.daily_limit,
        monthly_limit=quota.monthly_limit,
        current_daily_cost=quota.current_daily_cost,
        current_monthly_cost=quota.current_monthly_cost,
        current_daily_tokens=quota.current_daily_tokens,
        current_monthly_tokens=quota.current_monthly_tokens,
        daily_remaining=quota.get_daily_remaining(),
        monthly_remaining=quota.get_monthly_remaining(),
        daily_usage_percent=quota.get_usage_percent("daily"),
        monthly_usage_percent=quota.get_usage_percent("monthly"),
        alert_threshold_percent=quota.alert_threshold_percent,
        auto_disable_on_limit=quota.auto_disable_on_limit,
        daily_reset_at=quota.daily_reset_at,
        monthly_reset_at=quota.monthly_reset_at,
    )


@router.put("/{provider_name}/quota")
async def update_provider_quota(
    provider_name: str,
    quota_update: QuotaConfigUpdate,
    db: Session = Depends(get_db),
):
    """Update quota configuration for a provider."""
    quota_service = AIQuotaService(db)
    quota = quota_service._get_or_create_quota(provider_name)

    # Update fields
    for field, value in quota_update.model_dump(exclude_unset=True).items():
        setattr(quota, field, value)

    db.commit()
    db.refresh(quota)

    logger.info(f"Updated quota config for {provider_name}")

    return {
        "message": f"Quota updated for {provider_name}",
        "quota": QuotaResponse(
            provider_name=quota.provider_name,
            daily_limit=quota.daily_limit,
            monthly_limit=quota.monthly_limit,
            current_daily_cost=quota.current_daily_cost,
            current_monthly_cost=quota.current_monthly_cost,
            current_daily_tokens=quota.current_daily_tokens,
            current_monthly_tokens=quota.current_monthly_tokens,
            daily_remaining=quota.get_daily_remaining(),
            monthly_remaining=quota.get_monthly_remaining(),
            daily_usage_percent=quota.get_usage_percent("daily"),
            monthly_usage_percent=quota.get_usage_percent("monthly"),
            alert_threshold_percent=quota.alert_threshold_percent,
            auto_disable_on_limit=quota.auto_disable_on_limit,
            daily_reset_at=quota.daily_reset_at,
            monthly_reset_at=quota.monthly_reset_at,
        ),
    }


@router.post("/{provider_name}/quota/reset")
async def reset_provider_quota(
    provider_name: str,
    period: str = Query(..., regex="^(daily|monthly|both)$"),
    db: Session = Depends(get_db),
):
    """Manually reset quota counters."""
    quota_service = AIQuotaService(db)
    quota = quota_service._get_or_create_quota(provider_name)

    now = datetime.now()

    if period in ["daily", "both"]:
        quota.current_daily_cost = 0.0
        quota.current_daily_tokens = 0
        quota.daily_reset_at = now

    if period in ["monthly", "both"]:
        quota.current_monthly_cost = 0.0
        quota.current_monthly_tokens = 0
        quota.monthly_reset_at = now

    db.commit()

    logger.info(f"Reset {period} quota for {provider_name}")

    return {
        "message": f"{period.capitalize()} quota reset for {provider_name}",
        "reset_at": now,
    }


# =============================================================================
# Usage Statistics Endpoints
# =============================================================================


@router.get("/{provider_name}/usage-stats", response_model=list[UsageStatsResponse])
async def get_usage_stats(
    provider_name: str | None = None,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to look back"),
    db: Session = Depends(get_db),
):
    """Get usage statistics for a provider."""
    quota_service = AIQuotaService(db)

    start_date = datetime.now() - timedelta(days=days)

    stats = quota_service.get_usage_stats(
        provider_name=provider_name,
        start_date=start_date,
    )

    return stats["stats"]


@router.get("/{provider_name}/usage-logs")
async def get_usage_logs(
    provider_name: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    job_id: str | None = Query(default=None),
    errors_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """Get detailed usage logs for a provider."""

    stmt = sa.select(AIProviderUsageLog).where(AIProviderUsageLog.provider_name == provider_name)

    if job_id:
        stmt = stmt.where(AIProviderUsageLog.job_id == job_id)

    if errors_only:
        stmt = stmt.where(AIProviderUsageLog.is_error)

    stmt = stmt.order_by(AIProviderUsageLog.created_at.desc())
    stmt = stmt.offset(offset).limit(limit)

    logs = db.execute(stmt).scalars().all()

    # Count total
    count_stmt = (
        sa.select(sa.func.count())
        .select_from(AIProviderUsageLog)
        .where(AIProviderUsageLog.provider_name == provider_name)
    )
    if job_id:
        count_stmt = count_stmt.where(AIProviderUsageLog.job_id == job_id)
    if errors_only:
        count_stmt = count_stmt.where(AIProviderUsageLog.is_error)

    total = db.execute(count_stmt).scalar()

    return {
        "logs": [
            {
                "id": log.id,
                "provider": log.provider_name,
                "model": log.model_name,
                "job_id": log.job_id,
                "request_type": log.request_type,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "total_cost": log.total_cost,
                "response_time_ms": log.response_time_ms,
                "is_error": log.is_error,
                "error_message": log.error_message,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/usage-report/summary")
async def get_usage_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get overall usage summary across all providers."""

    start_date = datetime.now() - timedelta(days=days)

    # Overall stats
    stmt = sa.select(
        sa.func.count(AIProviderUsageLog.id).label("total_requests"),
        sa.func.sum(AIProviderUsageLog.total_tokens).label("total_tokens"),
        sa.func.sum(AIProviderUsageLog.total_cost).label("total_cost"),
        sa.func.avg(AIProviderUsageLog.response_time_ms).label("avg_response_time"),
        sa.func.sum(sa.case((AIProviderUsageLog.is_error, 1), else_=0)).label("error_count"),
    ).where(AIProviderUsageLog.created_at >= start_date)

    result = db.execute(stmt).first()

    # Per-provider breakdown
    provider_stmt = (
        sa.select(
            AIProviderUsageLog.provider_name,
            sa.func.count(AIProviderUsageLog.id).label("requests"),
            sa.func.sum(AIProviderUsageLog.total_cost).label("cost"),
        )
        .where(AIProviderUsageLog.created_at >= start_date)
        .group_by(AIProviderUsageLog.provider_name)
    )

    provider_stats = db.execute(provider_stmt).all()

    return {
        "period_days": days,
        "start_date": start_date,
        "end_date": datetime.now(),
        "summary": {
            "total_requests": result.total_requests or 0,
            "total_tokens": int(result.total_tokens or 0),
            "total_cost": float(result.total_cost or 0.0),
            "avg_response_time_ms": float(result.avg_response_time or 0.0),
            "error_count": result.error_count or 0,
            "success_rate": (
                ((result.total_requests - result.error_count) / result.total_requests * 100)
                if result.total_requests > 0
                else 0.0
            ),
        },
        "by_provider": [
            {
                "provider": row.provider_name,
                "requests": row.requests,
                "cost": float(row.cost or 0.0),
            }
            for row in provider_stats
        ],
    }
