"""
AI Provider Quota Management Service.

Handles quota checking, usage tracking, and cost calculation.
"""

import time
from collections import OrderedDict
from datetime import UTC, datetime, timedelta

import httpx
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.ai_provider_config import AIProviderConfig
from app.models.ai_provider_usage import AIProviderQuota, AIProviderUsageLog
from app.services.ai_providers.base import AIGenerateResponse

logger = get_logger(__name__)

# Constants for token pricing calculations
TOKENS_PER_MILLION = 1_000_000
TOKENS_PER_THOUSAND = 1_000


# Quota check cache with automatic cleanup
# Cache stores (can_proceed: bool, exception: Optional[Exception], timestamp: float)
class QuotaCache:
    """Thread-safe quota check cache with automatic cleanup."""

    def __init__(self, max_size: int = 100, cleanup_interval: int = 300):
        """
        Initialize quota cache.

        Args:
            max_size: Maximum number of cache entries
            cleanup_interval: Time interval in seconds for automatic cleanup
        """
        self._cache: OrderedDict[str, tuple[bool, Exception | None, float]] = OrderedDict()
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

        # Monitoring metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    def get(self, key: str, ttl: int) -> tuple[bool, Exception | None] | None:
        """
        Get cached value if still valid.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            Cached (can_proceed, exception) tuple if valid, None otherwise
        """
        # Perform periodic cleanup
        self._cleanup_if_needed()

        if key in self._cache:
            can_proceed, exception, timestamp = self._cache[key]
            current_time = time.time()

            # Check if cache entry is still valid
            if current_time - timestamp < ttl:
                # Move to end (LRU)
                self._cache.move_to_end(key)
                self._hits += 1
                return (can_proceed, exception)
            else:
                # Expired entry, remove it
                del self._cache[key]
                self._expirations += 1

        self._misses += 1
        return None

    def set(self, key: str, can_proceed: bool, exception: Exception | None) -> None:
        """
        Set cache value.

        Args:
            key: Cache key
            can_proceed: Whether quota check passed
            exception: Exception to cache (if any)
        """
        current_time = time.time()

        # Remove oldest entry if cache is full
        if len(self._cache) >= self._max_size:
            # Remove oldest (first) item
            self._cache.popitem(last=False)
            self._evictions += 1
            logger.debug("Quota cache full, removed oldest entry")

        # Add/update entry
        self._cache[key] = (can_proceed, exception, current_time)

    def _cleanup_if_needed(self) -> None:
        """Remove expired entries if cleanup interval has elapsed."""
        current_time = time.time()

        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        # Perform cleanup
        from app.core.config import settings

        default_ttl = settings.task_quota_check_cache_ttl

        # Find and remove expired entries
        keys_to_remove = []
        for key, (_, _, timestamp) in self._cache.items():
            if current_time - timestamp >= default_ttl * 2:  # Double TTL for cleanup
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

        if keys_to_remove:
            self._expirations += len(keys_to_remove)
            logger.debug(f"Quota cache cleanup: removed {len(keys_to_remove)} expired entries")

        self._last_cleanup = current_time

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Quota cache cleared")

    def get_stats(self) -> dict[str, any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary containing cache metrics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests) if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "evictions": self._evictions,
            "expirations": self._expirations,
            "total_requests": total_requests,
        }


# Global quota cache instance
_quota_cache = QuotaCache(max_size=100, cleanup_interval=300)


class QuotaPauseException(Exception):
    """Exception raised to pause a job due to quota limit."""

    def __init__(self, provider: str, limit_type: str, reason: str, resume_at: datetime):
        self.provider = provider
        self.limit_type = limit_type
        self.reason = reason
        self.resume_at = resume_at
        super().__init__(
            f"{provider} {limit_type} quota exceeded. "
            f"Task paused and will resume at {resume_at.isoformat()}"
        )


class QuotaExceededException(Exception):
    """Exception raised when quota is exceeded."""

    def __init__(self, provider: str, limit_type: str, current: float, limit: float):
        self.provider = provider
        self.limit_type = limit_type
        self.current = current
        self.limit = limit
        super().__init__(f"{provider} {limit_type} quota exceeded: ${current:.4f} / ${limit:.2f}")


class AIQuotaService:
    """
    Service for managing AI provider quotas and usage tracking.
    """

    def __init__(self, session: Session):
        """
        Initialize quota service.

        Args:
            session: Database session
        """
        self.session = session

    def check_quota(self, provider_name: str) -> None:
        """
        Check if provider has available quota.

        Args:
            provider_name: Name of the provider

        Raises:
            QuotaExceededException: If quota is exceeded
        """
        quota = self._get_or_create_quota(provider_name)

        # Reset counters if needed
        self._reset_quota_if_needed(quota)

        # Check daily limit
        if quota.is_daily_limit_exceeded():
            logger.warning(
                f"{provider_name} daily quota exceeded: "
                f"${quota.current_daily_cost:.4f} / ${quota.daily_limit:.2f}"
            )

            # Auto-disable provider if configured
            if quota.auto_disable_on_limit:
                self._disable_provider(provider_name)

            raise QuotaExceededException(
                provider=provider_name,
                limit_type="daily",
                current=quota.current_daily_cost,
                limit=quota.daily_limit,
            )

        # Check monthly limit
        if quota.is_monthly_limit_exceeded():
            logger.warning(
                f"{provider_name} monthly quota exceeded: "
                f"${quota.current_monthly_cost:.4f} / ${quota.monthly_limit:.2f}"
            )

            # Auto-disable provider if configured
            if quota.auto_disable_on_limit:
                self._disable_provider(provider_name)

            raise QuotaExceededException(
                provider=provider_name,
                limit_type="monthly",
                current=quota.current_monthly_cost,
                limit=quota.monthly_limit,
            )

        # Check if alert should be sent
        if quota.should_send_alert():
            self._send_quota_alert(quota)

    def check_quota_with_pause(self, provider_name: str, cache_ttl: int | None = None) -> None:
        """
        Check if provider has available quota, pause task instead of raising exception.

        This method is used during translation tasks. If quota is exceeded, it raises
        QuotaPauseException which will pause the task and schedule automatic resume.

        Includes caching to reduce database queries during translation loops.

        Args:
            provider_name: Name of the provider
            cache_ttl: Cache time-to-live in seconds (None = use config default)

        Raises:
            QuotaPauseException: If quota is exceeded (task should be paused)
        """
        global _quota_cache

        # Get cache TTL from config if not provided
        if cache_ttl is None:
            from app.core.config import settings

            cache_ttl = settings.task_quota_check_cache_ttl

        # Check cache
        cached_result = _quota_cache.get(provider_name, cache_ttl)
        if cached_result is not None:
            can_proceed, exception = cached_result
            if not can_proceed and exception:
                # Re-raise cached exception
                raise exception
            return  # Quota OK (cached)

        # Cache miss or expired - perform actual check
        exception_to_cache = None
        can_proceed = True

        try:
            quota = self._get_or_create_quota(provider_name)

            # Reset counters if needed
            self._reset_quota_if_needed(quota)

            # Check daily limit
            if quota.is_daily_limit_exceeded():
                logger.warning(
                    f"{provider_name} daily quota exceeded, pausing task: "
                    f"${quota.current_daily_cost:.4f} / ${quota.daily_limit:.2f}"
                )

                # Calculate resume time (next day at same time)
                resume_at = datetime.now(UTC) + timedelta(days=1)

                exception_to_cache = QuotaPauseException(
                    provider=provider_name,
                    limit_type="daily",
                    reason="daily_quota_exceeded",
                    resume_at=resume_at,
                )
                can_proceed = False

            # Check monthly limit
            elif quota.is_monthly_limit_exceeded():
                logger.warning(
                    f"{provider_name} monthly quota exceeded, pausing task: "
                    f"${quota.current_monthly_cost:.4f} / ${quota.monthly_limit:.2f}"
                )

                # Calculate resume time (next month on same day)
                now = datetime.now(UTC)
                if now.month == 12:
                    resume_at = now.replace(year=now.year + 1, month=1)
                else:
                    resume_at = now.replace(month=now.month + 1)

                exception_to_cache = QuotaPauseException(
                    provider=provider_name,
                    limit_type="monthly",
                    reason="monthly_quota_exceeded",
                    resume_at=resume_at,
                )
                can_proceed = False

            # Check if alert should be sent
            if can_proceed and quota.should_send_alert():
                self._send_quota_alert(quota)

            # Update cache
            _quota_cache.set(provider_name, can_proceed, exception_to_cache)

            # Raise exception if quota exceeded
            if not can_proceed:
                raise exception_to_cache

        except QuotaPauseException:
            # Re-raise quota pause exceptions
            raise
        except Exception as e:
            # Don't cache other exceptions, but log them
            logger.error(f"Quota check error for {provider_name}: {e}", exc_info=True)
            # Allow task to proceed on check failure (fail-open)
            _quota_cache.set(provider_name, True, None)

    def log_usage(
        self,
        provider_name: str,
        model_name: str,
        response: AIGenerateResponse,
        request_type: str = "generate",
        job_id: str | None = None,
        user_id: str | None = None,
        prompt_preview: str | None = None,
        response_preview: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_time_ms: int | None = None,
    ) -> AIProviderUsageLog:
        """
        Log API usage and update quota counters.

        Args:
            provider_name: Provider name
            model_name: Model name
            response: AI response object
            request_type: Type of request
            job_id: Optional job ID
            user_id: Optional user ID
            prompt_preview: First 200 chars of prompt
            response_preview: First 200 chars of response
            temperature: Temperature parameter
            max_tokens: Max tokens parameter
            response_time_ms: Response time in milliseconds

        Returns:
            AIProviderUsageLog: Created log entry
        """
        # Calculate cost
        input_cost, output_cost, total_cost = self._calculate_cost(
            provider_name=provider_name,
            model_name=model_name,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

        # Create log entry
        log_entry = AIProviderUsageLog(
            provider_name=provider_name,
            model_name=model_name,
            job_id=job_id,
            user_id=user_id,
            request_type=request_type,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=(response.input_tokens or 0) + (response.output_tokens or 0),
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            temperature=temperature,
            max_tokens=max_tokens,
            finish_reason=response.finish_reason,
            response_time_ms=response_time_ms,
            is_error=False,
            prompt_preview=prompt_preview[:200] if prompt_preview else None,
            response_preview=response_preview[:200] if response_preview else None,
        )

        self.session.add(log_entry)
        self.session.flush()

        # Update quota counters
        self._update_quota_counters(provider_name, total_cost, log_entry.total_tokens or 0)

        logger.info(
            f"Logged usage: {provider_name}:{model_name} - "
            f"${total_cost:.6f} ({response.input_tokens}/{response.output_tokens} tokens)"
        )

        return log_entry

    def log_error(
        self,
        provider_name: str,
        model_name: str,
        error_message: str,
        request_type: str = "generate",
        job_id: str | None = None,
        user_id: str | None = None,
    ) -> AIProviderUsageLog:
        """
        Log API error.

        Args:
            provider_name: Provider name
            model_name: Model name
            error_message: Error message
            request_type: Type of request
            job_id: Optional job ID
            user_id: Optional user ID

        Returns:
            AIProviderUsageLog: Created log entry
        """
        log_entry = AIProviderUsageLog(
            provider_name=provider_name,
            model_name=model_name,
            job_id=job_id,
            user_id=user_id,
            request_type=request_type,
            is_error=True,
            error_message=error_message[:500] if error_message else None,
            total_cost=0.0,
        )

        self.session.add(log_entry)
        self.session.flush()

        return log_entry

    def get_usage_stats(
        self,
        provider_name: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """
        Get usage statistics.

        Args:
            provider_name: Optional provider name filter
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            dict: Usage statistics
        """
        # Build query
        query = sa.select(
            AIProviderUsageLog.provider_name,
            sa.func.count(AIProviderUsageLog.id).label("request_count"),
            sa.func.sum(AIProviderUsageLog.total_tokens).label("total_tokens"),
            sa.func.sum(AIProviderUsageLog.total_cost).label("total_cost"),
            sa.func.avg(AIProviderUsageLog.response_time_ms).label("avg_response_time"),
            sa.func.sum(sa.case((AIProviderUsageLog.is_error, 1), else_=0)).label("error_count"),
        ).group_by(AIProviderUsageLog.provider_name)

        if provider_name:
            query = query.where(AIProviderUsageLog.provider_name == provider_name)

        if start_date:
            query = query.where(AIProviderUsageLog.created_at >= start_date)

        if end_date:
            query = query.where(AIProviderUsageLog.created_at <= end_date)

        results = self.session.execute(query).all()

        stats = []
        for row in results:
            stats.append(
                {
                    "provider": row.provider_name,
                    "request_count": row.request_count,
                    "total_tokens": int(row.total_tokens or 0),
                    "total_cost": float(row.total_cost or 0.0),
                    "avg_response_time_ms": float(row.avg_response_time or 0.0),
                    "error_count": row.error_count,
                    "success_rate": (
                        (row.request_count - row.error_count) / row.request_count * 100
                        if row.request_count > 0
                        else 0.0
                    ),
                }
            )

        return {
            "stats": stats,
            "total_cost": sum(s["total_cost"] for s in stats),
            "total_requests": sum(s["request_count"] for s in stats),
        }

    def _get_or_create_quota(self, provider_name: str) -> AIProviderQuota:
        """Get or create quota record for provider."""
        stmt = sa.select(AIProviderQuota).where(AIProviderQuota.provider_name == provider_name)
        quota = self.session.execute(stmt).scalar_one_or_none()

        if not quota:
            quota = AIProviderQuota(
                provider_name=provider_name,
                daily_reset_at=datetime.now(UTC),
                monthly_reset_at=datetime.now(UTC),
            )
            self.session.add(quota)
            self.session.flush()

        return quota

    def _reset_quota_if_needed(self, quota: AIProviderQuota) -> None:
        """Reset quota counters if period has elapsed."""
        now = datetime.now(UTC)
        modified = False

        # Check daily reset
        if quota.daily_reset_at:
            days_elapsed = (now - quota.daily_reset_at).days
            if days_elapsed >= 1:
                logger.info(f"Resetting daily quota for {quota.provider_name}")
                quota.current_daily_cost = 0.0
                quota.current_daily_tokens = 0
                quota.daily_reset_at = now
                modified = True

        # Check monthly reset
        if quota.monthly_reset_at:
            # Check if month has changed
            if now.year > quota.monthly_reset_at.year or (
                now.year == quota.monthly_reset_at.year and now.month > quota.monthly_reset_at.month
            ):
                logger.info(f"Resetting monthly quota for {quota.provider_name}")
                quota.current_monthly_cost = 0.0
                quota.current_monthly_tokens = 0
                quota.monthly_reset_at = now
                modified = True

        if modified:
            self.session.flush()

    def _update_quota_counters(
        self,
        provider_name: str,
        cost: float,
        tokens: int,
    ) -> None:
        """Update quota usage counters."""
        quota = self._get_or_create_quota(provider_name)

        quota.current_daily_cost += cost
        quota.current_monthly_cost += cost
        quota.current_daily_tokens += tokens
        quota.current_monthly_tokens += tokens

        self.session.flush()

    def _calculate_cost(
        self,
        provider_name: str,
        model_name: str,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> tuple[float | None, float | None, float]:
        """
        Calculate cost based on token usage and model pricing.

        Returns:
            tuple: (input_cost, output_cost, total_cost) in USD
        """
        # Get model pricing from AI model configuration
        from app.models.ai_model_config import AIModelConfig

        stmt = sa.select(AIModelConfig).where(
            AIModelConfig.provider_name == provider_name, AIModelConfig.model_name == model_name
        )
        model_config = self.session.execute(stmt).scalar_one_or_none()

        if not model_config:
            # Try fallback to old ModelRegistry for backward compatibility
            from app.models.model_registry import ModelRegistry

            stmt = sa.select(ModelRegistry).where(
                ModelRegistry.provider == provider_name, ModelRegistry.name == model_name
            )
            model_record = self.session.execute(stmt).scalar_one_or_none()

            if model_record:
                logger.debug(f"Using legacy ModelRegistry pricing for {provider_name}:{model_name}")
                input_cost = None
                output_cost = None

                if input_tokens and model_record.cost_input_per_1k:
                    input_cost = (
                        input_tokens / TOKENS_PER_THOUSAND
                    ) * model_record.cost_input_per_1k

                if output_tokens and model_record.cost_output_per_1k:
                    output_cost = (
                        output_tokens / TOKENS_PER_THOUSAND
                    ) * model_record.cost_output_per_1k

                total_cost = (input_cost or 0.0) + (output_cost or 0.0)
                return input_cost, output_cost, total_cost

            # No pricing information available
            logger.warning(
                f"Model {provider_name}:{model_name} not found in configuration, "
                f"cost calculation skipped"
            )
            return None, None, 0.0

        # Calculate cost using new AIModelConfig pricing (per 1M tokens)
        input_cost = None
        output_cost = None

        if input_tokens and model_config.input_price is not None:
            input_cost = (input_tokens / TOKENS_PER_MILLION) * model_config.input_price

        if output_tokens and model_config.output_price is not None:
            output_cost = (output_tokens / TOKENS_PER_MILLION) * model_config.output_price

        total_cost = (input_cost or 0.0) + (output_cost or 0.0)

        # Update model usage statistics
        if total_cost > 0:
            model_config.usage_count += 1
            model_config.total_input_tokens += input_tokens or 0
            model_config.total_output_tokens += output_tokens or 0
            self.session.flush()

        return input_cost, output_cost, total_cost

    def _disable_provider(self, provider_name: str) -> None:
        """Disable provider when quota exceeded."""
        stmt = sa.select(AIProviderConfig).where(AIProviderConfig.provider_name == provider_name)
        config = self.session.execute(stmt).scalar_one_or_none()

        if config:
            config.is_enabled = False
            self.session.flush()
            logger.warning(f"Auto-disabled provider {provider_name} due to quota limit")

    def _send_quota_alert(self, quota: AIProviderQuota) -> None:
        """Send alert when quota threshold reached."""
        now = datetime.now(UTC)

        # Don't send alert if one was sent recently (within 1 hour)
        if quota.last_alert_sent_at:
            time_since_last = now - quota.last_alert_sent_at
            if time_since_last < timedelta(hours=1):
                return

        daily_percent = quota.get_usage_percent("daily")
        monthly_percent = quota.get_usage_percent("monthly")

        logger.warning(
            f"Quota alert for {quota.provider_name}: "
            f"Daily {daily_percent:.1f}%, Monthly {monthly_percent:.1f}%"
        )

        if settings.alert_webhook_url:
            payload = {
                "provider": quota.provider_name,
                "daily_percent": daily_percent,
                "monthly_percent": monthly_percent,
                "timestamp": now.isoformat(),
                "message": "AI provider quota threshold reached",
            }
            headers = {"Content-Type": "application/json"}

            if settings.alert_webhook_token:
                headers["Authorization"] = f"Bearer {settings.alert_webhook_token}"

            try:
                response = httpx.post(
                    settings.alert_webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=settings.alert_webhook_timeout,
                )
                response.raise_for_status()
            except Exception as exc:
                logger.error(f"Failed to send quota alert webhook: {exc}")

        quota.last_alert_sent_at = now
        self.session.flush()
