"""
Task log persistence helpers.

Centralizes progress event construction and sampling so sync workers and async
event publishing follow the same persistence policy.
"""

import json
from datetime import datetime
from threading import Lock

from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.models.task_log import TaskLog

logger = get_logger(__name__)

TASK_LOG_PROGRESS_PERSIST_STEP = 5.0
TASK_LOG_PERSIST_INTERVAL_SECONDS = 2.0
TASK_LOG_LINE_PERSIST_EVERY = 20
TERMINAL_TASK_STATUSES = {"completed", "failed", "paused", "cancelled", "canceled"}

_persist_state: dict[tuple[str, str, str], dict[str, float | int]] = {}
_persist_lock = Lock()


def build_job_event_data(
    *,
    job_id: str,
    phase: str,
    status: str,
    progress: float,
    timestamp: datetime,
    completed: int | None = None,
    total: int | None = None,
    error: str | None = None,
    event_type: str | None = None,
    index: int | None = None,
    source: str | None = None,
    translated: str | None = None,
) -> dict:
    event_data = {
        "job_id": job_id,
        "phase": phase,
        "status": status,
        "progress": progress,
        "timestamp": timestamp.isoformat(),
    }

    if event_type:
        event_data["type"] = event_type
    if completed is not None:
        event_data["completed"] = completed
    if total is not None:
        event_data["total"] = total
    if error:
        event_data["error"] = error
    if index is not None:
        event_data["index"] = index
    if source is not None:
        event_data["source"] = source
    if translated is not None:
        event_data["translated"] = translated

    return event_data


def should_persist_task_log(
    *,
    job_id: str,
    phase: str,
    progress: float,
    timestamp: datetime,
    completed: int | None = None,
    total: int | None = None,
    error: str | None = None,
    event_type: str | None = None,
    index: int | None = None,
) -> bool:
    if error:
        return True

    if event_type == "line":
        if index is None:
            return False
        if index == 1:
            return True
        if total is not None and index >= total:
            return True
        return index % TASK_LOG_LINE_PERSIST_EVERY == 0

    if phase in {"completed", "failed", "writeback"}:
        return True

    if completed is not None and total is not None and total > 0 and completed >= total:
        return True

    state_key = (job_id, phase, event_type or "progress")

    with _persist_lock:
        previous = _persist_state.get(state_key)
        if previous is None:
            _persist_state[state_key] = {
                "progress": progress,
                "timestamp": timestamp.timestamp(),
                "completed": completed or 0,
            }
            return True

        progress_delta = progress - float(previous["progress"])
        elapsed = timestamp.timestamp() - float(previous["timestamp"])
        completed_delta = (completed or 0) - int(previous["completed"])

        should_persist = (
            progress_delta >= TASK_LOG_PROGRESS_PERSIST_STEP
            or elapsed >= TASK_LOG_PERSIST_INTERVAL_SECONDS
            or completed_delta > 0
        )

        if should_persist:
            _persist_state[state_key] = {
                "progress": progress,
                "timestamp": timestamp.timestamp(),
                "completed": completed or 0,
            }

        return should_persist


def clear_task_log_sampling_state(job_id: str) -> None:
    with _persist_lock:
        keys_to_remove = [key for key in _persist_state if key[0] == job_id]
        for key in keys_to_remove:
            del _persist_state[key]


def persist_task_log_if_needed(
    *,
    job_id: str,
    phase: str,
    status: str,
    progress: float,
    timestamp: datetime,
    completed: int | None = None,
    total: int | None = None,
    error: str | None = None,
    event_type: str | None = None,
    index: int | None = None,
    persist_override: bool | None = None,
) -> bool:
    persist_to_db = (
        persist_override
        if persist_override is not None
        else should_persist_task_log(
            job_id=job_id,
            phase=phase,
            progress=progress,
            timestamp=timestamp,
            completed=completed,
            total=total,
            error=error,
            event_type=event_type,
            index=index,
        )
    )

    if not persist_to_db:
        return False

    try:
        with SessionLocal() as session:
            log_entry = TaskLog(
                job_id=job_id,
                timestamp=timestamp,
                phase=phase,
                status=status,
                progress=progress,
                completed=completed,
                total=total,
                extra_data=json.dumps({"error": error}) if error else None,
            )
            session.add(log_entry)
            session.commit()
        if status in TERMINAL_TASK_STATUSES:
            clear_task_log_sampling_state(job_id)
        return True
    except Exception as exc:
        logger.warning(f"Failed to persist task log: {exc}")
        return False
