"""Runtime helpers for AI model catalog sync settings and task lifecycle."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.setting import Setting

logger = get_logger(__name__)


@dataclass
class CatalogSyncConfig:
    enabled: bool
    interval_seconds: int
    catalog_url: str


_catalog_sync_task: asyncio.Task[None] | None = None


def _convert_db_value(setting: Setting | None, fallback: Any) -> Any:
    if setting is None:
        return fallback
    if setting.value_type == "int":
        return int(setting.value)
    if setting.value_type == "bool":
        return setting.value.lower() in ("true", "1", "yes")
    if setting.value_type == "float":
        return float(setting.value)
    return setting.value


def load_catalog_sync_config(db: Session) -> CatalogSyncConfig:
    keys = {
        "ai_models_auto_sync_enabled": settings.ai_models_auto_sync_enabled,
        "ai_models_auto_sync_interval_seconds": settings.ai_models_auto_sync_interval_seconds,
        "ai_models_catalog_url": settings.ai_models_catalog_url,
    }

    resolved: dict[str, Any] = {}
    for key, fallback in keys.items():
        setting = db.scalar(select(Setting).where(Setting.key == key))
        resolved[key] = _convert_db_value(setting, fallback)

    settings.ai_models_auto_sync_enabled = bool(resolved["ai_models_auto_sync_enabled"])
    settings.ai_models_auto_sync_interval_seconds = int(
        resolved["ai_models_auto_sync_interval_seconds"]
    )
    settings.ai_models_catalog_url = str(resolved["ai_models_catalog_url"])

    return CatalogSyncConfig(
        enabled=settings.ai_models_auto_sync_enabled,
        interval_seconds=settings.ai_models_auto_sync_interval_seconds,
        catalog_url=settings.ai_models_catalog_url,
    )


async def ensure_catalog_sync_task(loop_coro_factory) -> None:
    global _catalog_sync_task

    if settings.ai_models_auto_sync_enabled:
        if _catalog_sync_task is None or _catalog_sync_task.done():
            _catalog_sync_task = asyncio.create_task(loop_coro_factory())
            logger.info("Started AI model catalog sync background task")
        return

    if _catalog_sync_task is not None and not _catalog_sync_task.done():
        _catalog_sync_task.cancel()
        await asyncio.gather(_catalog_sync_task, return_exceptions=True)
        logger.info("Stopped AI model catalog sync background task")
    _catalog_sync_task = None


async def shutdown_catalog_sync_task() -> None:
    global _catalog_sync_task

    if _catalog_sync_task is not None and not _catalog_sync_task.done():
        _catalog_sync_task.cancel()
        await asyncio.gather(_catalog_sync_task, return_exceptions=True)
    _catalog_sync_task = None


def reload_catalog_sync_settings_from_db() -> CatalogSyncConfig:
    with next(get_db()) as db:
        return load_catalog_sync_config(db)
