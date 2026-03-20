import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.services.ai_quota_service import QuotaExceededException, QuotaCache


@pytest.mark.unit
class TestQuotaExceededException:
    def test_message_with_limit(self):
        exc = QuotaExceededException(provider="openai", limit_type="daily", current=9.5, limit=10.0)
        assert "openai" in str(exc)
        assert "daily" in str(exc)
        assert "9.5" in str(exc)

    def test_message_with_none_limit(self):
        exc = QuotaExceededException(
            provider="openai", limit_type="monthly", current=100.0, limit=None
        )
        assert "N/A" in str(exc)

    def test_attributes(self):
        exc = QuotaExceededException(provider="claude", limit_type="daily", current=5.0, limit=10.0)
        assert exc.provider == "claude"
        assert exc.limit_type == "daily"
        assert exc.current == 5.0
        assert exc.limit == 10.0


@pytest.mark.unit
class TestQuotaCache:
    def test_miss_returns_none(self):
        cache = QuotaCache()
        assert cache.get("provider_x", ttl=60) is None

    def test_set_and_get(self):
        cache = QuotaCache()
        cache.set("provider_x", True, None)
        result = cache.get("provider_x", ttl=60)
        assert result is not None
        can_proceed, exception = result
        assert can_proceed is True
        assert exception is None

    def test_get_stats_returns_dict(self):
        cache = QuotaCache()
        stats = cache.get_stats()
        assert isinstance(stats, dict)
        assert "size" in stats
        assert "hits" in stats
