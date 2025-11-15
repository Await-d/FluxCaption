"""
SSE (Server-Sent Events) support for real-time progress updates.

Provides event publishing and subscription for job progress streaming.
"""

import json
import asyncio
from typing import AsyncGenerator
from redis import asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EventPublisher:
    """
    Publish events to Redis for SSE streaming.

    Workers publish progress events, API subscribes and forwards to clients.
    """

    def __init__(self, redis_url: str | None = None):
        """
        Initialize event publisher.

        Args:
            redis_url: Redis connection URL (defaults to settings)
        """
        self.redis_url = redis_url or settings.redis_url
        self._redis = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if not self._redis:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Event publisher connected to Redis")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Event publisher disconnected from Redis")

    async def publish_event(self, channel: str, event_data: dict) -> None:
        """
        Publish an event to a channel and store in history.

        Args:
            channel: Channel name (typically "job:{job_id}")
            event_data: Event data dictionary
        """
        if not self._redis:
            await self.connect()

        try:
            event_json = json.dumps(event_data)

            # Publish to subscribers
            await self._redis.publish(channel, event_json)

            # Store in history list (keep last 100 events)
            history_key = f"{channel}:history"
            await self._redis.lpush(history_key, event_json)
            await self._redis.ltrim(history_key, 0, 99)  # Keep only last 100
            await self._redis.expire(history_key, 3600)  # Auto-delete after 1 hour

            logger.info(f"Published event to {channel}: {event_data}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}", exc_info=True)

    async def publish_job_progress(
        self,
        job_id: str,
        phase: str,
        status: str,
        progress: float,
        completed: int | None = None,
        total: int | None = None,
        error: str | None = None,
    ) -> None:
        """
        Publish job progress event and save to database log.

        Args:
            job_id: Job ID
            phase: Current phase (pull, asr, mt, post, writeback)
            status: Status message
            progress: Progress percentage (0-100)
            completed: Completed units
            total: Total units
            error: Error message (if any)
        """
        from datetime import datetime, timezone
        
        # Generate timestamp ONCE for both event and database
        timestamp = datetime.now(timezone.utc)
        
        event_data = {
            "job_id": job_id,
            "phase": phase,
            "status": status,
            "progress": progress,
            "timestamp": timestamp.isoformat(),  # Include timestamp in event
        }

        if completed is not None:
            event_data["completed"] = completed

        if total is not None:
            event_data["total"] = total

        if error:
            event_data["error"] = error

        await self.publish_event(f"job:{job_id}", event_data)

        # Also save to database for historical viewing
        try:
            from app.core.db import SessionLocal
            from app.models.task_log import TaskLog

            with SessionLocal() as session:
                log_entry = TaskLog(
                    job_id=job_id,
                    timestamp=timestamp,  # Use the same timestamp as the event
                    phase=phase,
                    status=status,
                    progress=progress,
                    completed=completed,
                    total=total,
                    extra_data=json.dumps({"error": error}) if error else None,
                )
                session.add(log_entry)
                session.commit()
        except Exception as e:
            logger.warning(f"Failed to save task log to database: {e}")

    async def publish_config_change(
        self,
        setting_key: str,
        old_value: str,
        new_value: str,
        changed_by: str,
    ) -> None:
        """
        Publish configuration change event for worker reload.

        Args:
            setting_key: Setting key that was changed
            old_value: Old value
            new_value: New value
            changed_by: Username who made the change
        """
        from datetime import datetime, timezone

        event_data = {
            "event_type": "config_change",
            "setting_key": setting_key,
            "old_value": old_value,
            "new_value": new_value,
            "changed_by": changed_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Publish to config change channel
        await self.publish_event("config:changes", event_data)

        logger.info(
            f"Configuration change published: {setting_key} = {new_value} "
            f"(changed by {changed_by})"
        )


class EventSubscriber:
    """
    Subscribe to events from Redis for SSE streaming.

    API uses this to forward events to connected clients.
    """

    def __init__(self, redis_url: str | None = None):
        """
        Initialize event subscriber.

        Args:
            redis_url: Redis connection URL (defaults to settings)
        """
        self.redis_url = redis_url or settings.redis_url

    async def subscribe(self, channel: str) -> AsyncGenerator[dict, None]:
        """
        Subscribe to a channel and yield events.

        Args:
            channel: Channel name to subscribe to

        Yields:
            dict: Event data
        """
        redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

        try:
            pubsub = redis.pubsub()
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to channel: {channel}")

            # Skip the subscription confirmation message
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        yield event_data
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse event data: {e}")
                        continue

        except asyncio.CancelledError:
            logger.info(f"Subscription to {channel} cancelled")
        except Exception as e:
            logger.error(f"Error in subscription: {e}", exc_info=True)
        finally:
            await pubsub.unsubscribe(channel)
            await redis.close()
            logger.info(f"Unsubscribed from channel: {channel}")


# =============================================================================
# Singleton Instances
# =============================================================================

event_publisher = EventPublisher()
event_subscriber = EventSubscriber()


# =============================================================================
# SSE Response Generator
# =============================================================================

async def generate_sse_response(channel: str, initial_job_state: dict | None = None) -> AsyncGenerator[str, None]:
    """
    Generate SSE response stream with historical events.

    Args:
        channel: Channel to subscribe to
        initial_job_state: Optional initial job state to send first

    Yields:
        str: SSE formatted event
    """
    try:
        # Send initial job state if provided (to handle race conditions)
        if initial_job_state:
            sse_data = f"data: {json.dumps(initial_job_state)}\n\n"
            yield sse_data
            logger.info(f"Sent initial job state for {channel}")

        # Send historical events from Redis
        redis = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            history_key = f"{channel}:history"
            # Get last 100 events (in reverse chronological order)
            history_events = await redis.lrange(history_key, 0, -1)

            if history_events:
                # Reverse to get chronological order (oldest first)
                for event_json in reversed(history_events):
                    try:
                        sse_data = f"data: {event_json}\n\n"
                        yield sse_data
                    except Exception as e:
                        logger.error(f"Failed to send historical event: {e}")
                logger.info(f"Sent {len(history_events)} historical events for {channel}")
        finally:
            await redis.close()

        # Subscribe to real-time events
        async for event_data in event_subscriber.subscribe(channel):
            # Format as SSE
            sse_data = f"data: {json.dumps(event_data)}\n\n"
            yield sse_data

            # Check if job is complete
            if event_data.get("status") in ("success", "failed", "canceled"):
                break

    except asyncio.CancelledError:
        logger.info(f"SSE stream for {channel} cancelled by client")
    except Exception as e:
        logger.error(f"Error in SSE stream: {e}", exc_info=True)
        # Send error event
        error_event = {
            "error": str(e),
            "status": "error",
        }
        yield f"data: {json.dumps(error_event)}\n\n"
