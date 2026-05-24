import inspect

import pytest
from fastapi import APIRouter

from app.api.routers import (
    ai_models,
    ai_providers,
    auth,
    auto_translation_rules,
    cache,
    health,
    jellyfin,
    jobs,
    local_media,
    models,
    settings,
    system_config,
    translation_memory,
)


def _endpoint_by_name(router: APIRouter, name: str):
    for route in router.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint and endpoint.__name__ == name:
            return endpoint
    raise AssertionError(f"Route endpoint {name!r} not found")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("router", "endpoint_name"),
    [
        (jobs.router, "get_job"),
        (jobs.router, "list_jobs"),
        (jobs.router, "cancel_job"),
        (local_media.router, "scan_directory"),
        (local_media.router, "create_batch_local_jobs"),
        (models.router, "list_models"),
        (models.router, "test_model"),
        (models.router, "set_default_model"),
        (ai_models.router, "list_models"),
        (ai_models.router, "create_model"),
        (ai_models.router, "sync_catalog"),
        (auto_translation_rules.router, "list_rules"),
        (auto_translation_rules.router, "create_rule"),
        (ai_providers.router, "list_providers"),
        (ai_providers.router, "get_provider_quota"),
        (cache.router, "get_cache_stats"),
        (translation_memory.router, "list_translation_pairs"),
        (system_config.router, "get_system_config"),
        (settings.router, "get_settings"),
        (settings.router, "reset_settings_to_defaults"),
        (settings.router, "validate_settings"),
        (auth.router, "login"),
    ],
)
def test_sync_db_file_route_handlers_are_sync(router: APIRouter, endpoint_name: str):
    endpoint = _endpoint_by_name(router, endpoint_name)

    assert not inspect.iscoroutinefunction(endpoint)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("router", "endpoint_name"),
    [
        (jobs.router, "create_translation_job"),
        (jobs.router, "stream_job_progress"),
        (translation_memory.router, "re_proofread_translation"),
        (system_config.router, "update_system_config"),
        (settings.router, "update_settings"),
        (health.router, "health_check"),
        (health.router, "readiness_check"),
        (models.router, "delete_model"),
        (jobs.router, "create_translation_job"),
        (jellyfin.router, "list_library_items"),
        (jellyfin.router, "get_item_detail"),
        (jellyfin.router, "list_series_episodes"),
        (jellyfin.router, "manual_writeback"),
        (ai_providers.router, "check_provider_health"),
        (ai_providers.router, "test_provider_generation"),
    ],
)
def test_async_route_exceptions_remain_async(router: APIRouter, endpoint_name: str):
    endpoint = _endpoint_by_name(router, endpoint_name)

    assert inspect.iscoroutinefunction(endpoint)


@pytest.mark.unit
def test_auth_dependencies_are_sync():
    assert not inspect.iscoroutinefunction(auth.get_current_user)
    assert not inspect.iscoroutinefunction(auth.get_current_user_sse)
