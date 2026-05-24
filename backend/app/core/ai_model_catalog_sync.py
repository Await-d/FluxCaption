"""AI model catalog synchronization using opencode-compatible models.dev data."""

from __future__ import annotations

import json
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
import sqlalchemy as sa
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.ai_model_config import AIModelConfig
from app.models.ai_provider_config import AIProviderConfig
from app.models.setting import Setting

logger = get_logger(__name__)

MANAGED_TAG = "managed:models.dev"
COMPAT_TAG = "catalog:opencode-compatible"
CATALOG_FALLBACK_URLS = [
    "https://models.dev/api.json",
    "https://models.dev/_api.json",
]


@dataclass
class CatalogSyncResult:
    created: int = 0
    updated: int = 0
    merged: int = 0
    skipped: int = 0
    providers_created: int = 0


def _parse_tags(raw_tags: str | None) -> list[str]:
    if not raw_tags:
        return []
    try:
        value = json.loads(raw_tags)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _dump_tags(tags: list[str]) -> str | None:
    unique = list(dict.fromkeys(tag for tag in tags if tag))
    return json.dumps(unique, ensure_ascii=False) if unique else None


def _build_tags(model_id: str, model_data: dict[str, Any]) -> list[str]:
    tags = [MANAGED_TAG, COMPAT_TAG, f"model:{model_id}"]

    if model_data.get("reasoning"):
        tags.append("capability:reasoning")
    if model_data.get("attachment"):
        tags.append("capability:attachments")
    if model_data.get("tool_call"):
        tags.append("capability:tool-calls")

    modalities = model_data.get("modalities") or {}
    for item in modalities.get("input", []):
        tags.append(f"input:{item}")
    for item in modalities.get("output", []):
        tags.append(f"output:{item}")

    status = model_data.get("status")
    if status:
        tags.append(f"status:{status}")

    family = model_data.get("family")
    if family:
        tags.append(f"family:{family}")

    return list(dict.fromkeys(tags))


def _build_description(model_data: dict[str, Any]) -> str:
    bits: list[str] = []
    family = model_data.get("family")
    if family:
        bits.append(f"Family: {family}")
    release_date = model_data.get("release_date")
    if release_date:
        bits.append(f"Release: {release_date}")
    status = model_data.get("status")
    if status:
        bits.append(f"Status: {status}")
    return " | ".join(bits)


def _resolve_model_type(model_data: dict[str, Any]) -> str:
    if model_data.get("reasoning"):
        return "reasoning"
    return "chat"


def _ensure_provider(db: Session, provider_id: str, provider_data: dict[str, Any]) -> bool:
    existing = (
        db.query(AIProviderConfig)
        .filter(AIProviderConfig.provider_name == provider_id)
        .first()
    )
    if existing:
        return False

    db.add(
        AIProviderConfig(
            provider_name=provider_id,
            display_name=provider_data.get("name") or provider_id,
            is_enabled=False,
            base_url=provider_data.get("api"),
            timeout=30,
            priority=0,
            description="Synced from models.dev (opencode-compatible catalog)",
        )
    )
    db.flush()
    return True


def _record_last_sync(db: Session, synced_at: datetime) -> None:
    setting = db.query(Setting).filter(Setting.key == "ai_models_last_catalog_sync_at").first()
    value = synced_at.isoformat()

    if setting is None:
        db.add(
            Setting(
                key="ai_models_last_catalog_sync_at",
                value=value,
                value_type="string",
                category="ai_models",
                description="Last successful AI model catalog sync timestamp",
                is_editable=False,
            )
        )
    else:
        setting.value = value


def _repair_legacy_model_ids(db: Session) -> int:
    repaired = 0
    rows = db.execute(sa.text("SELECT id FROM ai_model_configs")).fetchall()

    for row in rows:
        raw_id = row[0]
        try:
            uuid.UUID(str(raw_id).strip())
            continue
        except (ValueError, TypeError, AttributeError):
            new_id = str(uuid.uuid4())
            db.execute(
                sa.text("UPDATE ai_model_configs SET id = :new_id WHERE id = :old_id"),
                {"new_id": new_id, "old_id": raw_id},
            )
            repaired += 1

    if repaired:
        logger.warning(f"Repaired {repaired} legacy AI model IDs before catalog sync")

    return repaired


async def fetch_models_catalog() -> dict[str, Any]:
    configured_url = settings.ai_models_catalog_url.rstrip("/") + "/api.json"
    candidates = [configured_url, *[url for url in CATALOG_FALLBACK_URLS if url != configured_url]]
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        last_error: Exception | None = None
        for catalog_url in candidates:
            try:
                response = await client.get(
                    catalog_url,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("Invalid models catalog payload")
                return data
            except Exception as e:
                last_error = e
                logger.warning(f"Failed to fetch AI model catalog from {catalog_url}: {e}")

                try:
                    request = urllib.request.Request(catalog_url, headers=headers)
                    with urllib.request.urlopen(request, timeout=20) as response2:
                        body = response2.read().decode("utf-8")
                    data = json.loads(body)
                    if not isinstance(data, dict):
                        raise ValueError("Invalid models catalog payload")
                    return data
                except Exception as urllib_error:
                    last_error = urllib_error
                    logger.warning(
                        f"Fallback urllib fetch failed for AI model catalog from {catalog_url}: {urllib_error}"
                    )

        if last_error is not None:
            raise last_error
        raise RuntimeError("No AI model catalog source available")


async def sync_ai_models_from_catalog(
    db: Session,
    *,
    provider_name: str | None = None,
) -> CatalogSyncResult:
    result = CatalogSyncResult()
    payload = await fetch_models_catalog()
    now = datetime.utcnow()
    _repair_legacy_model_ids(db)

    for provider_id, provider_data in payload.items():
        if provider_name and provider_id != provider_name:
            continue
        if not isinstance(provider_data, dict):
            result.skipped += 1
            continue

        if _ensure_provider(db, provider_id, provider_data):
            result.providers_created += 1

        models = provider_data.get("models")
        if not isinstance(models, dict):
            result.skipped += 1
            continue

        for model_id, model_data in models.items():
            if not isinstance(model_data, dict):
                result.skipped += 1
                continue

            existing = (
                db.query(AIModelConfig)
                .filter(
                    and_(
                        AIModelConfig.provider_name == provider_id,
                        AIModelConfig.model_name == model_id,
                    )
                )
                .first()
            )

            description = _build_description(model_data)
            cost = model_data.get("cost") or {}
            limits = model_data.get("limit") or {}
            synced_tags = _build_tags(model_id, model_data)

            synced_fields = {
                "display_name": model_data.get("name") or model_id,
                "model_type": _resolve_model_type(model_data),
                "context_window": limits.get("context"),
                "max_output_tokens": limits.get("output"),
                "input_price": cost.get("input"),
                "output_price": cost.get("output"),
                "pricing_notes": "Synced from models.dev (opencode-compatible catalog)",
                "description": description or None,
                "is_available": True,
                "last_checked": now,
            }

            if existing is None:
                db.add(
                    AIModelConfig(
                        provider_name=provider_id,
                        model_name=model_id,
                        is_enabled=True,
                        is_default=False,
                        priority=0,
                        tags=_dump_tags(synced_tags),
                        **synced_fields,
                    )
                )
                result.created += 1
                continue

            existing_tags = _parse_tags(existing.tags)
            is_managed = MANAGED_TAG in existing_tags

            if is_managed:
                for field, value in synced_fields.items():
                    setattr(existing, field, value)
                existing.tags = _dump_tags(synced_tags)
                result.updated += 1
                continue

            merged_tags = list(dict.fromkeys(existing_tags + [COMPAT_TAG]))
            existing.tags = _dump_tags(merged_tags)
            existing.last_checked = now
            existing.is_available = True

            for field, value in synced_fields.items():
                if field in {"pricing_notes", "description", "display_name"}:
                    if getattr(existing, field):
                        continue
                if field in {"context_window", "max_output_tokens", "input_price", "output_price", "model_type"}:
                    if getattr(existing, field) is not None:
                        continue
                setattr(existing, field, value)

            result.merged += 1

    _record_last_sync(db, now)

    db.commit()
    logger.info(
        "Synced AI model catalog from models.dev",
        extra={
            "catalog_created": result.created,
            "catalog_updated": result.updated,
            "catalog_merged": result.merged,
            "catalog_skipped": result.skipped,
            "catalog_providers_created": result.providers_created,
        },
    )
    return result
