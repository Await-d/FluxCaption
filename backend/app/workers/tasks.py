"""
Celery tasks for background processing.

Defines tasks for translation, ASR, and library scanning.
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from celery import Task

from app.core.config import settings
from app.core.db import session_scope
from app.core.events import event_publisher
from app.core.logging import JobLogContext, get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


# Helper to run async code in sync context
def run_async(coro):
    """Run an async coroutine in a synchronous context."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


def save_task_log_sync(
    job_id: str,
    phase: str,
    status: str,
    progress: float,
    completed: int = None,
    total: int = None,
    error: str = None,
):
    """
    Synchronously save task log to database and publish to Redis for SSE streaming.

    This is used in progress callbacks where async operations cause event loop conflicts.
    """
    try:
        import json
        from datetime import datetime

        import redis

        from app.core.db import SessionLocal
        from app.models.task_log import TaskLog

        timestamp = datetime.now(UTC)

        # Save to database
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

        # Also publish to Redis for real-time SSE streaming
        try:
            from app.core.config import settings

            redis_client = redis.from_url(settings.redis_url, decode_responses=True)

            event_data = {
                "job_id": job_id,
                "phase": phase,
                "status": status,
                "progress": progress,
                "timestamp": timestamp.isoformat(),
            }
            if completed is not None:
                event_data["completed"] = completed
            if total is not None:
                event_data["total"] = total
            if error:
                event_data["error"] = error

            channel = f"job:{job_id}"
            event_json = json.dumps(event_data)

            # Publish to subscribers
            redis_client.publish(channel, event_json)

            # Also save to history list (keep last 100 events)
            history_key = f"{channel}:history"
            redis_client.lpush(history_key, event_json)
            redis_client.ltrim(history_key, 0, 99)  # Keep only last 100
            redis_client.expire(history_key, 3600)  # Auto-delete after 1 hour

            redis_client.close()
        except Exception as redis_error:
            logger.warning(f"Failed to publish to Redis: {redis_error}")

    except Exception as e:
        logger.warning(f"Failed to save task log to database: {e}")


# =============================================================================
# Checkpoint/Resume Helper Functions
# =============================================================================


def save_checkpoint(session, job_id: str, phase: str, **kwargs):
    """
    Save a checkpoint for task resumption.

    Args:
        session: Database session
        job_id: Job ID
        phase: Completed phase name
        **kwargs: Additional checkpoint data (asr_output_path, completed_target_langs, etc.)
    """
    from datetime import datetime

    from app.models.translation_job import TranslationJob

    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
    if not job:
        logger.warning(f"Job {job_id} not found, cannot save checkpoint")
        return

    # Load existing completed phases
    completed_phases = []
    if job.completed_phases:
        try:
            completed_phases = json.loads(job.completed_phases)
        except:
            completed_phases = []

    # Add new phase if not already present
    if phase and phase not in completed_phases:
        completed_phases.append(phase)
        job.completed_phases = json.dumps(completed_phases)

    # Update checkpoint fields
    if "asr_output_path" in kwargs:
        job.asr_output_path = kwargs["asr_output_path"]

    if "completed_target_lang" in kwargs:
        # Load existing completed languages
        completed_langs = []
        if job.completed_target_langs:
            try:
                completed_langs = json.loads(job.completed_target_langs)
            except:
                completed_langs = []

        # Add new language if not already present
        lang = kwargs["completed_target_lang"]
        if lang not in completed_langs:
            completed_langs.append(lang)
            job.completed_target_langs = json.dumps(completed_langs)

    # Update checkpoint timestamp
    job.last_checkpoint_at = datetime.now(UTC)

    session.commit()
    logger.info(f"Checkpoint saved for job {job_id}: phase={phase}, data={kwargs}")


def check_phase_completed(job, phase: str) -> bool:
    """
    Check if a phase has been completed.

    Args:
        job: TranslationJob instance
        phase: Phase name to check

    Returns:
        bool: True if phase is completed
    """
    if not job.completed_phases:
        return False

    try:
        completed = json.loads(job.completed_phases)
        return phase in completed
    except:
        return False


def get_remaining_target_langs(job) -> list:
    """
    Get list of target languages that haven't been translated yet.

    Args:
        job: TranslationJob instance

    Returns:
        list: List of remaining target language codes
    """
    try:
        all_targets = json.loads(job.target_langs)

        if not job.completed_target_langs:
            return all_targets

        completed = json.loads(job.completed_target_langs)
        remaining = [lang for lang in all_targets if lang not in completed]

        return remaining
    except:
        # On error, return all targets
        try:
            return json.loads(job.target_langs)
        except:
            return []


# =============================================================================
# Base Task Class
# =============================================================================


class BaseTask(Task):
    """
    Base task class with common functionality.

    Provides error handling, logging, and progress tracking.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Called when task fails.

        Args:
            exc: Exception raised
            task_id: Task ID
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception info
        """
        logger.error(
            f"Task {self.name} failed: {exc}",
            exc_info=True,
            extra={"task_id": task_id, "task_args": args, "task_kwargs": kwargs},
        )

        # Last resort: ensure job status is updated in database
        # This handles cases where the task fails but status wasn't updated
        try:
            if args and len(args) > 0:
                job_id = args[0]  # First argument is usually job_id
                if isinstance(job_id, str):
                    with session_scope() as session:
                        from datetime import datetime

                        from app.models.translation_job import TranslationJob

                        job = (
                            session.query(TranslationJob)
                            .filter(TranslationJob.id == job_id)
                            .first()
                        )

                        if job and job.status == "running":
                            job.status = "failed"
                            if not job.error:
                                job.error = str(exc)
                            if not job.finished_at:
                                job.finished_at = datetime.now(UTC)
                            session.commit()
                            logger.info(
                                f"Job {job_id} status updated to failed in on_failure handler"
                            )
        except Exception as db_exc:
            logger.error(
                f"Failed to update job status in on_failure handler: {db_exc}", exc_info=True
            )

    def on_success(self, retval, task_id, args, kwargs):
        """
        Called when task succeeds.

        Args:
            retval: Return value
            task_id: Task ID
            args: Task positional arguments
            kwargs: Task keyword arguments
        """
        logger.info(
            f"Task {self.name} completed successfully",
            extra={"task_id": task_id, "retval": retval},
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Called when task is retried.

        Args:
            exc: Exception raised
            task_id: Task ID
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception info
        """
        logger.warning(
            f"Task {self.name} will be retried: {exc}",
            extra={"task_id": task_id},
        )


# =============================================================================
# Translation Tasks
# =============================================================================


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="app.workers.tasks.translate_subtitle_task",
    max_retries=3,
    default_retry_delay=60,
)
def translate_subtitle_task(self, job_id: str) -> dict:
    """
    Translate an existing subtitle file.

    Args:
        job_id: Translation job ID

    Returns:
        dict: Task result with status and output paths
    """

    with JobLogContext(job_id=job_id, phase="translate"):
        logger.info(f"Starting subtitle translation task for job {job_id}")

        try:
            # === 1. Load job from database ===
            with session_scope() as session:
                from app.models.translation_job import TranslationJob

                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()

                if not job:
                    raise ValueError(f"Job {job_id} not found")

                # Update job status
                job.status = "running"
                job.started_at = datetime.now(timezone.utc)
                job.current_phase = "init"
                session.commit()

                # Extract job data
            source_path = job.source_path
            source_lang = job.source_lang
            target_langs = json.loads(job.target_langs)
            model = job.model
            provider = job.provider  # Get AI provider from job
            item_id = job.item_id  # Extract item_id for writeback

            # === 2. Ensure model is available (with checkpoint support) ===
            from app.services.ollama_client import ollama_client

            # Check if model pull phase was already completed
            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                pull_completed = check_phase_completed(job, "pull")

            if not pull_completed:
                logger.info(f"Checking model availability: {model}")
                job.current_phase = "model_check"

                model_exists = run_async(ollama_client.check_model_exists(model))

                if not model_exists:
                    logger.info(f"Model {model} not found locally, pulling...")
                    job.current_phase = "pull"

                    # Publish pull start event
                    run_async(
                        event_publisher.publish_job_progress(
                            job_id=job_id,
                            phase="pull",
                            status="pulling",
                            progress=0,
                        )
                    )

                    # Pull model with progress callback
                    def pull_progress_callback(progress_data: dict):
                        # Forward progress to SSE
                        completed = progress_data.get("completed", 0)
                        total = progress_data.get("total", 0)
                        status_msg = progress_data.get("status", "")

                        if total > 0:
                            progress_pct = (completed / total) * 100
                        else:
                            progress_pct = 0

                        # Publish to Redis for SSE
                        try:
                            run_async(
                                event_publisher.publish_job_progress(
                                    job_id=job_id,
                                    phase="pull",
                                    status=status_msg,
                                    progress=progress_pct,
                                    completed=completed,
                                    total=total,
                                )
                            )
                        except Exception as e:
                            logger.warning(f"Failed to publish progress: {e}")

                    run_async(
                        ollama_client.pull_model(model, progress_callback=pull_progress_callback)
                    )
                    logger.info(f"Model {model} pulled successfully")

                    # Save checkpoint after successful pull
                    with session_scope() as session:
                        save_checkpoint(session, job_id, "pull")
                else:
                    logger.info(f"Model {model} already exists locally")
                    # Save checkpoint even if model exists (no pull needed)
                    with session_scope() as session:
                        save_checkpoint(session, job_id, "pull")
            else:
                logger.info("Model pull phase already completed, skipping...")

            # === 3. Load and translate subtitle ===
            from app.services.subtitle_service import SubtitleService

            if not source_path or not Path(source_path).exists():
                raise FileNotFoundError(f"Source subtitle file not found: {source_path}")

            output_dir = Path(settings.subtitle_output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Get remaining target languages (checkpoint support)
            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                remaining_langs = get_remaining_target_langs(job)

            # If all languages completed, use existing result paths
            if len(remaining_langs) == 0:
                logger.info("All target languages already translated, skipping translation phase")
                # Load existing result paths
                with session_scope() as session:
                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    if job.result_paths:
                        result_paths = json.loads(job.result_paths)
                    else:
                        result_paths = []
            else:
                logger.info(
                    f"Resuming translation: {len(remaining_langs)} languages remaining: {remaining_langs}"
                )

                # Load existing result paths if any
                with session_scope() as session:
                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    if job.result_paths:
                        result_paths = json.loads(job.result_paths)
                    else:
                        result_paths = []

                total_targets = len(target_langs)
                completed_count = total_targets - len(remaining_langs)

                for idx, target_lang in enumerate(remaining_langs):
                    actual_idx = completed_count + idx
                    logger.info(f"Translating to {target_lang} ({actual_idx + 1}/{total_targets})")

                    # === Check quota before starting translation ===
                    try:
                        from app.services.ai_quota_service import (
                            AIQuotaService,
                            QuotaPauseException,
                        )

                        with session_scope() as session:
                            quota_service = AIQuotaService(session)
                            quota_service.check_quota_with_pause(provider)
                    except QuotaPauseException as e:
                        # Pause the job - it will be automatically resumed later
                        logger.warning(f"Job {job_id} paused due to quota limit: {e}")

                        with session_scope() as session:
                            job = (
                                session.query(TranslationJob)
                                .filter(TranslationJob.id == job_id)
                                .first()
                            )
                            if job:
                                job.status = "paused"
                                job.pause_reason = e.reason
                                job.paused_at = datetime.now(timezone.utc)
                                job.resume_at = e.resume_at
                                job.error = f"Paused: {e.limit_type} quota exceeded"
                                session.commit()

                        # Publish pause event
                        run_async(
                            event_publisher.publish_job_progress(
                                job_id=job_id,
                                phase="mt",
                                status=f"paused: quota limit exceeded ({e.limit_type})",
                                progress=(actual_idx / total_targets) * 100,
                            )
                        )

                        # Stop processing further languages
                        break

                    with session_scope() as session:
                        job = (
                            session.query(TranslationJob)
                            .filter(TranslationJob.id == job_id)
                            .first()
                        )
                        job.current_phase = "mt"
                        session.commit()

                    # Publish translation start event for this language
                    run_async(
                        event_publisher.publish_job_progress(
                            job_id=job_id,
                            phase="mt",
                            status=f"translating to {target_lang} ({actual_idx + 1}/{total_targets})",
                            progress=(actual_idx / total_targets) * 100,
                        )
                    )

                    # Build output path
                    source_file = Path(source_path)
                    output_path = (
                        output_dir / f"{source_file.stem}_{target_lang}{source_file.suffix}"
                    )

                    # Progress callback for translation
                    def progress_callback(completed: int, total: int, message: str = ""):
                        progress_pct = (completed / total) * 100
                        base_progress = (actual_idx / total_targets) * 100
                        current_progress = base_progress + (progress_pct / total_targets)

                        # Use message if provided, otherwise use default
                        status_msg = message if message else f"Translating to {target_lang}"

                        # Save directly to database (sync) to avoid event loop conflicts
                        save_task_log_sync(
                            job_id=job_id,
                            phase="mt",
                            status=status_msg,
                            progress=current_progress,
                            completed=completed,
                            total=total,
                        )

                    # Get asset_id and media_name for translation memory
                    asset_id = None
                    media_name = None
                    if item_id:
                        with session_scope() as session:
                            from app.models.media_asset import MediaAsset

                            asset = session.query(MediaAsset).filter_by(item_id=item_id).first()
                            if asset:
                                asset_id = str(asset.id)
                                media_name = asset.name

                    # Perform translation with translation memory support
                    with session_scope() as session:
                        stats = run_async(
                            SubtitleService.translate_subtitle(
                                input_path=str(source_path),
                                output_path=str(output_path),
                                source_lang=source_lang,
                                target_lang=target_lang,
                                model=model,
                                provider=provider,
                                batch_size=settings.translation_batch_size,
                                preserve_formatting=settings.preserve_ass_styles,
                                enable_proofreading=settings.enable_translation_proofreading,
                                progress_callback=progress_callback,
                                db_session=session,
                                subtitle_id=None,
                                asset_id=asset_id,
                                media_name=media_name,
                            )
                        )

                    result_paths.append(str(output_path))
                    logger.info(f"Translation to {target_lang} completed: {stats}")

                    # Save checkpoint after each language completes
                    with session_scope() as session:
                        save_checkpoint(session, job_id, None, completed_target_lang=target_lang)
                        # Also save result paths progressively
                        job = (
                            session.query(TranslationJob)
                            .filter(TranslationJob.id == job_id)
                            .first()
                        )
                        job.result_paths = json.dumps(result_paths)
                        session.commit()

            # === 4. Writeback to Jellyfin (if item_id present) ===
            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                item_id = job.item_id if job else None

            if item_id:
                logger.info(f"Job has item_id {item_id}, performing writeback")

                from app.models.media_asset import MediaAsset
                from app.models.subtitle import Subtitle
                from app.services.writeback import WritebackService

                with session_scope() as session:
                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    job.current_phase = "writeback"
                    session.commit()

                run_async(
                    event_publisher.publish_job_progress(
                        job_id=job_id,
                        phase="writeback",
                        status="writing back to Jellyfin",
                        progress=95,
                    )
                )

                # Create subtitle records and writeback
                for idx, (output_path, target_lang) in enumerate(
                    zip(result_paths, target_langs, strict=False)
                ):
                    with session_scope() as session:
                        # Get or create media asset
                        asset = session.query(MediaAsset).filter_by(item_id=item_id).first()

                        if not asset:
                            logger.warning(
                                f"MediaAsset not found for item_id {item_id}, creating placeholder"
                            )
                            asset = MediaAsset(
                                item_id=item_id,
                                library_id="",
                                name=f"Item {item_id}",
                                type="Unknown",
                            )
                            session.add(asset)
                            session.flush()

                        # Calculate line count and word count
                        try:
                            import pysubs2

                            subs = pysubs2.load(output_path)
                            line_count = len(subs)
                            word_count = sum(len(event.text.split()) for event in subs)
                        except Exception as e:
                            logger.warning(f"Failed to calculate subtitle stats: {e}")
                            line_count = None
                            word_count = None

                        # Check if subtitle already exists (avoid duplicates)
                        existing_subtitle = (
                            session.query(Subtitle)
                            .filter(
                                Subtitle.asset_id == asset.id,
                                Subtitle.lang == target_lang,
                                Subtitle.origin == "mt",
                                Subtitle.source_lang == source_lang,
                            )
                            .first()
                        )

                        if existing_subtitle:
                            logger.info(
                                f"Subtitle already exists for {target_lang}, updating instead of creating duplicate"
                            )
                            existing_subtitle.storage_path = output_path
                            existing_subtitle.line_count = line_count
                            existing_subtitle.word_count = word_count
                            existing_subtitle.updated_at = datetime.now(timezone.utc)
                            subtitle = existing_subtitle
                        else:
                            # Create subtitle record
                            subtitle = Subtitle(
                                asset_id=asset.id,
                                lang=target_lang,
                                format=Path(output_path).suffix.lstrip("."),
                                storage_path=output_path,
                                origin="mt",
                                source_lang=source_lang,
                                is_uploaded=False,
                                line_count=line_count,
                                word_count=word_count,
                            )
                            session.add(subtitle)

                        session.commit()

                        # Perform writeback
                        try:
                            result = run_async(
                                WritebackService.writeback_subtitle(
                                    session=session,
                                    subtitle_id=str(subtitle.id),
                                    mode=None,  # Use default from settings
                                    force=False,
                                )
                            )
                            logger.info(f"Writeback successful for {target_lang}: {result}")
                        except Exception as e:
                            logger.error(f"Writeback failed for {target_lang}: {e}", exc_info=True)
                            # Continue with other languages even if one fails

            # === 5. Update job status ===
            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                job.status = "success"
                job.progress = 100.0
                job.finished_at = datetime.utcnow()
                job.current_phase = "completed"
                job.result_paths = json.dumps(result_paths)
                session.commit()

            # Publish completion event
            run_async(
                event_publisher.publish_job_progress(
                    job_id=job_id,
                    phase="completed",
                    status="success",
                    progress=100,
                )
            )

            logger.info(f"Subtitle translation completed for job {job_id}")

            return {
                "status": "success",
                "job_id": job_id,
                "result_paths": result_paths,
            }

        except Exception as exc:
            logger.error(f"Translation task failed for job {job_id}: {exc}", exc_info=True)

            # Retry on transient failures
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc)

            # Update job status to failed (final attempt)
            try:
                with session_scope() as session:
                    from app.models.translation_job import TranslationJob

                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    if job:
                        job.status = "failed"
                        job.error = str(exc)
                        job.finished_at = datetime.now(timezone.utc)
                        session.commit()
                        logger.info(f"Job {job_id} marked as failed in database")
            except Exception as db_exc:
                logger.error(f"Failed to update job status in database: {db_exc}", exc_info=True)

            raise


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="app.workers.tasks.asr_then_translate_task",
    max_retries=2,
    default_retry_delay=120,
)
def asr_then_translate_task(self, job_id: str) -> dict:
    """
    Extract audio, perform ASR, then translate.

    Complete pipeline: Media → Audio extraction → ASR → Translation → Writeback

    Args:
        job_id: Translation job ID

    Returns:
        dict: Task result with status and output paths
    """
    from datetime import datetime

    with JobLogContext(job_id=job_id, phase="asr"):
        logger.info(f"Starting ASR + translation task for job {job_id}")

        try:
            # === 1. Load job from database ===
            with session_scope() as session:
                from app.models.translation_job import TranslationJob

                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()

                if not job:
                    raise ValueError(f"Job {job_id} not found")

                # Update job status
                job.status = "running"
                job.started_at = datetime.now(UTC)
                job.current_phase = "init"
                session.commit()

                # Extract job data
                source_path = job.source_path  # Path to media file
                source_lang = job.source_lang
                target_langs = json.loads(job.target_langs)
                model = job.model
                provider = job.provider  # Get AI provider from job
                item_id = job.item_id

            # If source_path doesn't exist or is None, and we have item_id (Jellyfin), use audio streaming
            if item_id and (not source_path or not Path(source_path).exists()):
                if source_path:
                    logger.info(
                        f"Source path {source_path} not accessible, using Jellyfin audio stream for item {item_id}"
                    )
                else:
                    logger.info(
                        f"No source path provided, using Jellyfin audio stream for item {item_id}"
                    )

                from app.services.jellyfin_client import get_jellyfin_client

                jellyfin = get_jellyfin_client()

                # Get audio stream URL instead of downloading entire file
                try:
                    audio_stream_url = run_async(jellyfin.get_audio_stream_url(item_id))
                    source_path = audio_stream_url  # Use URL directly as source
                    logger.info("Using Jellyfin audio stream URL for extraction")

                    # Update job with stream URL
                    with session_scope() as session:
                        job = (
                            session.query(TranslationJob)
                            .filter(TranslationJob.id == job_id)
                            .first()
                        )
                        if job:
                            job.source_path = audio_stream_url
                            session.commit()
                except Exception as e:
                    logger.error(f"Failed to get audio stream URL from Jellyfin: {e}")
                    raise FileNotFoundError(f"Cannot access media for item {item_id}: {str(e)}")

            # Check if source is URL or local file
            is_url = source_path and source_path.startswith(("http://", "https://"))
            if not is_url and (not source_path or not Path(source_path).exists()):
                raise FileNotFoundError(f"Source media file not found: {source_path}")

            # Define paths that will be used
            audio_temp_dir = Path(settings.temp_dir) / f"asr_{job_id}"
            audio_path = audio_temp_dir / "audio.wav"
            asr_output_dir = Path(settings.subtitle_output_dir) / "asr"
            asr_output_dir.mkdir(parents=True, exist_ok=True)
            asr_subtitle_path = asr_output_dir / f"{job_id}_original.srt"

            # Check if ASR phase was already completed (checkpoint support)
            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                asr_completed = check_phase_completed(job, "asr")
                # Also check if we have saved ASR output path
                if job.asr_output_path and Path(job.asr_output_path).exists():
                    asr_subtitle_path = Path(job.asr_output_path)
                    if source_lang == "auto":
                        # Try to load detected language from saved subtitle metadata
                        # For now, we'll need to re-run ASR if source_lang was auto
                        # In the future, could save detected language to job metadata
                        pass

            if not asr_completed:
                # === 2. Extract audio from media (with checkpoint support) ===
                from app.services.audio_extractor import AudioExtractor

                extract_completed = False
                with session_scope() as session:
                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    extract_completed = check_phase_completed(job, "extract")

                if not extract_completed:
                    logger.info(f"Extracting audio from {source_path}")

                    with session_scope() as session:
                        job = (
                            session.query(TranslationJob)
                            .filter(TranslationJob.id == job_id)
                            .first()
                        )
                        job.current_phase = "extract"
                        session.commit()

                    run_async(
                        event_publisher.publish_job_progress(
                            job_id=job_id,
                            phase="extract",
                            status="extracting audio",
                            progress=5,
                        )
                    )

                    # Create temp directory for audio
                    audio_temp_dir.mkdir(parents=True, exist_ok=True)

                    extractor = AudioExtractor()

                    def extract_progress_callback(progress: float):
                        try:
                            run_async(
                                event_publisher.publish_job_progress(
                                    job_id=job_id,
                                    phase="extract",
                                    status="extracting audio",
                                    progress=5 + (progress * 0.15),  # 5-20%
                                )
                            )
                        except Exception as e:
                            logger.warning(f"Failed to publish extract progress: {e}")

                    extractor.extract_audio(
                        video_path=str(source_path),
                        output_path=str(audio_path),
                        sample_rate=16000,
                        channels=1,
                        progress_callback=extract_progress_callback,
                    )

                    logger.info(f"Audio extracted to {audio_path}")

                    # Save checkpoint after extraction
                    with session_scope() as session:
                        save_checkpoint(session, job_id, "extract")
                else:
                    logger.info("Audio extraction phase already completed, skipping...")

                # === 3. Perform ASR (faster-whisper) with checkpoint support ===
                from app.services.asr_service import get_asr_service

                logger.info("Starting ASR transcription")

                with session_scope() as session:
                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    job.current_phase = "asr"
                    session.commit()

                # Check audio duration to determine if segmentation is needed
                extractor = AudioExtractor()
                audio_duration = extractor._get_duration(str(audio_path))

                # Determine if we need to split audio
                should_split = (
                    audio_duration and audio_duration > settings.asr_auto_segment_threshold
                )

                audio_segments_dir = None  # Initialize to None

                if should_split:
                    # Split audio into segments
                    logger.info(
                        f"Audio duration {audio_duration:.1f}s exceeds threshold "
                        f"({settings.asr_auto_segment_threshold}s), splitting into segments"
                    )
                    audio_segments_dir = temp_dir / "audio_segments"
                    audio_segments = extractor.split_audio(
                        video_path=str(source_path),
                        output_dir=str(audio_segments_dir),
                        segment_duration=settings.asr_segment_duration,
                        overlap=settings.asr_segment_overlap,
                        sample_rate=16000,
                        channels=1,
                    )
                    total_segments = len(audio_segments)
                    logger.info(f"Split audio into {total_segments} segments")
                else:
                    # Process as single audio file
                    audio_segments = [
                        {
                            "path": str(audio_path),
                            "index": 0,
                            "start": 0,
                            "duration": audio_duration or 0,
                        }
                    ]
                    total_segments = 1

                run_async(
                    event_publisher.publish_job_progress(
                        job_id=job_id,
                        phase="asr",
                        status=f"transcribing audio ({total_segments} {'segment' if total_segments == 1 else 'segments'})",
                        progress=20,
                    )
                )

                asr_service = get_asr_service()

                # Determine ASR language
                asr_lang = None if source_lang == "auto" else source_lang

                # Process segments with parallel processing and error recovery
                import time
                from concurrent.futures import ThreadPoolExecutor, as_completed
                from threading import Lock

                # Thread-safe progress tracking
                progress_lock = Lock()
                completed_segments = 0
                detected_language = None
                all_segments_results = [None] * total_segments  # Pre-allocate results

                def process_segment_with_retry(
                    segment_idx: int, audio_segment: dict, detected_lang: str = None
                ) -> tuple:
                    """
                    Process a single segment with retry logic.

                    Returns:
                        tuple: (segment_idx, result_dict, error_message)
                    """
                    segment_path = audio_segment["path"]
                    segment_info = (
                        f"segment {segment_idx}/{total_segments}" if total_segments > 1 else "audio"
                    )
                    output_path = (
                        str(asr_subtitle_path)
                        if total_segments == 1
                        else str(temp_dir / f"asr_segment_{segment_idx:04d}.srt")
                    )

                    max_retries = settings.asr_segment_max_retries

                    for attempt in range(1, max_retries + 1):
                        try:
                            logger.info(
                                f"Processing {segment_info}: {segment_path} (attempt {attempt}/{max_retries})"
                            )

                            # Publish start event (sync version for thread safety)
                            save_task_log_sync(
                                job_id=job_id,
                                phase="asr",
                                status=f"transcribing {segment_info}"
                                + (f" (retry {attempt})" if attempt > 1 else ""),
                                progress=20 + ((segment_idx - 1) / total_segments) * 30,  # 20-50%
                            )

                            def asr_progress_callback(completed: int, total: int):
                                try:
                                    nonlocal completed_segments
                                    with progress_lock:
                                        # Calculate progress within current segment
                                        segment_progress = (completed / total) if total > 0 else 0
                                        overall_progress = (
                                            20
                                            + (
                                                (segment_idx - 1 + segment_progress)
                                                / total_segments
                                            )
                                            * 30
                                        )

                                        status_msg = (
                                            f"transcribing {segment_info} ({completed} segments)"
                                            if total_segments > 1
                                            else f"transcribing ({completed} segments)"
                                        )

                                        # Use sync version to avoid event loop issues in threads
                                        save_task_log_sync(
                                            job_id=job_id,
                                            phase="asr",
                                            status=status_msg,
                                            progress=overall_progress,
                                            completed=completed,
                                            total=total,
                                        )
                                except Exception as e:
                                    logger.warning(f"Failed to publish ASR progress: {e}")

                            # Perform ASR transcription
                            segment_result = asr_service.transcribe_to_srt(
                                audio_path=segment_path,
                                output_path=output_path,
                                language=asr_lang or detected_lang,
                                vad_filter=settings.asr_vad_filter,
                                vad_threshold=settings.asr_vad_threshold,
                                beam_size=settings.asr_beam_size,
                                best_of=settings.asr_best_of,
                                progress_callback=asr_progress_callback,
                            )

                            logger.info(
                                f"Successfully processed {segment_info}: {segment_result.get('num_segments', 0)} segments"
                            )
                            return (segment_idx, segment_result, None)

                        except Exception as e:
                            error_msg = f"Attempt {attempt}/{max_retries} failed for {segment_info}: {str(e)}"
                            logger.error(error_msg, exc_info=True)

                            if attempt < max_retries:
                                # Wait before retry with exponential backoff
                                wait_time = 2**attempt  # 2, 4, 8 seconds
                                logger.info(f"Retrying {segment_info} in {wait_time} seconds...")
                                time.sleep(wait_time)
                            else:
                                # All retries exhausted
                                logger.error(f"All retries exhausted for {segment_info}")
                                return (segment_idx, None, error_msg)

                    return (segment_idx, None, "Unknown error")

                # Determine parallelism level
                if total_segments == 1:
                    # Single segment, no parallelism needed
                    max_workers = 1
                else:
                    # Limit parallel workers based on config and available segments
                    max_workers = min(settings.asr_max_parallel_segments, total_segments)

                logger.info(
                    f"Processing {total_segments} segments with {max_workers} parallel workers"
                )

                # Process segments in parallel
                failed_segments = []

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all segment processing tasks
                    future_to_segment = {}

                    # First, process the first segment to detect language
                    if total_segments > 1 and asr_lang is None:
                        logger.info("Processing first segment for language detection...")
                        first_idx, first_result, first_error = process_segment_with_retry(
                            1, audio_segments[0]
                        )

                        if first_result:
                            all_segments_results[0] = first_result
                            detected_language = first_result.get("language")
                            logger.info(
                                f"Detected language from first segment: {detected_language}"
                            )

                            with progress_lock:
                                completed_segments = 1
                        else:
                            failed_segments.append((1, first_error))
                            logger.error(f"First segment failed: {first_error}")

                        # Submit remaining segments
                        for idx in range(2, total_segments + 1):
                            future = executor.submit(
                                process_segment_with_retry,
                                idx,
                                audio_segments[idx - 1],
                                detected_language,
                            )
                            future_to_segment[future] = idx
                    else:
                        # Submit all segments
                        for idx, audio_segment in enumerate(audio_segments, start=1):
                            future = executor.submit(
                                process_segment_with_retry, idx, audio_segment, detected_language
                            )
                            future_to_segment[future] = idx

                    # Collect results as they complete
                    for future in as_completed(future_to_segment):
                        segment_idx, result, error = future.result()

                        if result:
                            all_segments_results[segment_idx - 1] = result

                            # Update detected language from first successful segment
                            if not detected_language and result.get("language"):
                                with progress_lock:
                                    detected_language = result.get("language")
                                logger.info(f"Detected language: {detected_language}")

                            with progress_lock:
                                completed_segments += 1
                                logger.info(
                                    f"Completed {completed_segments}/{total_segments} segments"
                                )
                        else:
                            failed_segments.append((segment_idx, error))

                # Check if we have any successful segments
                successful_results = [r for r in all_segments_results if r is not None]

                if not successful_results:
                    raise Exception(
                        f"All {total_segments} segments failed to process. Errors: {failed_segments}"
                    )

                if failed_segments:
                    logger.warning(
                        f"Completed with {len(failed_segments)} failed segments out of {total_segments}. "
                        f"Failed: {failed_segments}"
                    )

                    # Publish warning event
                    run_async(
                        event_publisher.publish_job_progress(
                            job_id=job_id,
                            phase="asr",
                            status=f"Completed with {len(failed_segments)} failed segments",
                            progress=50,
                            error=f"Failed segments: {[idx for idx, _ in failed_segments]}",
                        )
                    )
                else:
                    logger.info(f"Successfully processed all {total_segments} segments")

                # Merge segments if multiple
                if total_segments > 1:
                    logger.info(
                        f"Merging ASR segment results (successful: {len(successful_results)}/{total_segments})"
                    )

                    # Prepare segment files for merging (only successful ones)
                    segment_files_to_merge = []
                    for idx, (audio_seg, result) in enumerate(
                        zip(audio_segments, all_segments_results, strict=False), start=1
                    ):
                        if result is None:
                            # Skip failed segments
                            logger.warning(f"Skipping failed segment {idx} in merge")
                            continue

                        segment_srt_path = temp_dir / f"asr_segment_{idx:04d}.srt"
                        if segment_srt_path.exists():
                            segment_files_to_merge.append(
                                {
                                    "path": str(segment_srt_path),
                                    "start": audio_seg["start"],
                                    "duration": audio_seg["duration"],
                                }
                            )

                    # Merge SRT files with proper timestamp adjustment
                    from app.services.subtitle_service import SubtitleService

                    merge_result = SubtitleService.merge_srt_segments(
                        segment_files=segment_files_to_merge,
                        output_path=str(asr_subtitle_path),
                    )

                    logger.info(
                        f"Successfully merged {merge_result['total_segments']} segments into "
                        f"{merge_result['total_events']} subtitle events "
                        f"(removed {merge_result['duplicates_removed']} duplicates)"
                    )

                    # Clean up individual segment files
                    for seg_file in segment_files_to_merge:
                        try:
                            Path(seg_file["path"]).unlink(missing_ok=True)
                        except Exception as e:
                            logger.warning(f"Failed to delete segment file {seg_file['path']}: {e}")

                    # Clean up segment audio files
                    if audio_segments_dir and audio_segments_dir.exists():
                        import shutil

                        try:
                            shutil.rmtree(audio_segments_dir, ignore_errors=True)
                            logger.info("Cleaned up audio segments directory")
                        except Exception as e:
                            logger.warning(f"Failed to clean up audio segments: {e}")

                    asr_result = {
                        "num_segments": merge_result["total_events"],
                        "language": detected_language or asr_lang or "unknown",
                        "segments_processed": len(successful_results),
                        "segments_failed": len(failed_segments),
                    }
                else:
                    asr_result = (
                        successful_results[0]
                        if successful_results
                        else {
                            "num_segments": 0,
                            "language": "unknown",
                        }
                    )

                logger.info(
                    f"ASR complete: {asr_result['num_segments']} segments, "
                    f"language={asr_result['language']}"
                )

                # Save checkpoint after ASR with output path
                with session_scope() as session:
                    save_checkpoint(session, job_id, "asr", asr_output_path=str(asr_subtitle_path))

                # Clean up audio file after successful ASR
                if audio_path.exists():
                    audio_path.unlink(missing_ok=True)
                    logger.info(f"Cleaned up temporary audio file: {audio_path}")
            else:
                logger.info("ASR phase already completed, using existing subtitle")
                # Load ASR result from existing file
                asr_result = {"num_segments": 0, "language": source_lang}
                if asr_subtitle_path.exists():
                    # Count lines in SRT file for segment count
                    try:
                        with open(asr_subtitle_path, encoding="utf-8") as f:
                            content = f.read()
                            # Simple count: number of timestamp lines
                            asr_result["num_segments"] = content.count("-->")
                    except:
                        pass

            # Update source language if it was auto-detected
            if source_lang == "auto":
                source_lang = asr_result["language"]

            # Save ASR-generated source subtitle to database
            from app.models.media_asset import MediaAsset
            from app.models.subtitle import Subtitle

            with session_scope() as session:
                # Get or create media asset
                asset = session.query(MediaAsset).filter_by(item_id=item_id).first()

                if not asset:
                    logger.warning(
                        f"MediaAsset not found for item_id {item_id}, creating placeholder"
                    )
                    asset = MediaAsset(
                        item_id=item_id, library_id="", name=f"Item {item_id}", type="Unknown"
                    )
                    session.add(asset)
                    session.flush()

                # Calculate word count for ASR subtitle
                try:
                    import pysubs2

                    subs = pysubs2.load(str(asr_subtitle_path))
                    asr_word_count = sum(len(event.text.split()) for event in subs)
                except Exception as e:
                    logger.warning(f"Failed to calculate ASR word count: {e}")
                    asr_word_count = None

                # Check if ASR subtitle already exists (avoid duplicates)
                existing_asr_subtitle = (
                    session.query(Subtitle)
                    .filter(
                        Subtitle.asset_id == asset.id,
                        Subtitle.lang == source_lang,
                        Subtitle.origin == "asr",
                    )
                    .first()
                )

                if existing_asr_subtitle:
                    logger.info(
                        f"ASR subtitle already exists for {source_lang}, updating instead of creating duplicate"
                    )
                    existing_asr_subtitle.storage_path = str(asr_subtitle_path)
                    existing_asr_subtitle.line_count = asr_result.get("num_segments", 0)
                    existing_asr_subtitle.word_count = asr_word_count
                    existing_asr_subtitle.updated_at = datetime.now(UTC)
                    asr_source_subtitle = existing_asr_subtitle
                else:
                    # Create subtitle record for ASR source
                    asr_source_subtitle = Subtitle(
                        asset_id=asset.id,
                        lang=source_lang,
                        format="srt",
                        storage_path=str(asr_subtitle_path),
                        origin="asr",
                        source_lang=None,  # This IS the source, no source_lang
                        is_uploaded=False,
                        line_count=asr_result.get("num_segments", 0),
                        word_count=asr_word_count,
                    )
                    session.add(asr_source_subtitle)

                session.commit()
                logger.info(
                    f"Saved ASR source subtitle to database: {source_lang}, {asr_result.get('num_segments', 0)} segments"
                )

            # === 4. Translate generated subtitle (with checkpoint support) ===
            from app.services.subtitle_service import SubtitleService

            logger.info("Starting translation of ASR-generated subtitle")

            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                job.current_phase = "mt"
                job.source_lang = source_lang  # Update with detected language
                session.commit()

            # Publish MT phase start event
            run_async(
                event_publisher.publish_job_progress(
                    job_id=job_id,
                    phase="mt",
                    status=f"starting translation from {source_lang} to {', '.join(target_langs)}",
                    progress=50,
                )
            )

            output_dir = Path(settings.subtitle_output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Get remaining target languages (checkpoint support)
            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                remaining_langs = get_remaining_target_langs(job)

            # If all languages completed, use existing result paths
            if len(remaining_langs) == 0:
                logger.info("All target languages already translated, skipping translation phase")
                # Load existing result paths
                with session_scope() as session:
                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    if job.result_paths:
                        result_paths = json.loads(job.result_paths)
                    else:
                        result_paths = []
            else:
                logger.info(
                    f"Resuming translation: {len(remaining_langs)} languages remaining: {remaining_langs}"
                )

                # Load existing result paths if any
                with session_scope() as session:
                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    if job.result_paths:
                        result_paths = json.loads(job.result_paths)
                    else:
                        result_paths = []

                total_targets = len(target_langs)
                completed_count = total_targets - len(remaining_langs)

                for idx, target_lang in enumerate(remaining_langs):
                    actual_idx = completed_count + idx
                    logger.info(f"Translating to {target_lang} ({actual_idx + 1}/{total_targets})")

                    # Check quota before translation
                    try:
                        from app.services.ai_quota_service import (
                            AIQuotaService,
                            QuotaPauseException,
                        )

                        with session_scope() as session:
                            quota_service = AIQuotaService(session)
                            quota_service.check_quota_with_pause(provider)
                    except QuotaPauseException as e:
                        # Pause the job - it will be automatically resumed later
                        logger.warning(f"Job {job_id} paused due to quota limit: {e}")

                        with session_scope() as session:
                            job = (
                                session.query(TranslationJob)
                                .filter(TranslationJob.id == job_id)
                                .first()
                            )
                            if job:
                                job.status = "paused"
                                job.pause_reason = e.reason
                                job.paused_at = datetime.now(UTC)
                                job.resume_at = e.resume_at
                                job.error = f"Paused: {e.limit_type} quota exceeded"
                                session.commit()

                        # Publish pause event
                        run_async(
                            event_publisher.publish_job_progress(
                                job_id=job_id,
                                phase="mt",
                                status=f"paused: quota limit exceeded ({e.limit_type})",
                                progress=50 + (actual_idx / total_targets) * 30,
                            )
                        )

                        # Stop processing further languages
                        break

                    # Publish translation start event for this language
                    run_async(
                        event_publisher.publish_job_progress(
                            job_id=job_id,
                            phase="mt",
                            status=f"translating to {target_lang} ({actual_idx + 1}/{total_targets})",
                            progress=50 + (actual_idx / total_targets) * 30,
                        )
                    )

                    # Build output path
                    source_file = Path(asr_subtitle_path)
                    output_path = output_dir / f"{source_file.stem}_{target_lang}.srt"

                    # Progress callback for translation
                    def progress_callback(completed: int, total: int, message: str = ""):
                        base_progress = 50 + (actual_idx / total_targets) * 30
                        if total > 0:
                            current_progress = base_progress + (
                                (completed / total) * (30 / total_targets)
                            )
                        else:
                            current_progress = base_progress

                        # Use message if provided, otherwise use default
                        status_msg = message if message else f"Translating to {target_lang}"

                        # Save directly to database (sync) to avoid event loop conflicts
                        save_task_log_sync(
                            job_id=job_id,
                            phase="mt",
                            status=status_msg,
                            progress=current_progress,
                            completed=completed,
                            total=total,
                        )

                    # Get asset_id and media_name for translation memory
                    asset_id = None
                    media_name = None
                    if item_id:
                        with session_scope() as session:
                            from app.models.media_asset import MediaAsset

                            asset = session.query(MediaAsset).filter_by(item_id=item_id).first()
                            if asset:
                                asset_id = str(asset.id)
                                media_name = asset.name

                    # Perform translation with translation memory support
                    with session_scope() as session:
                        stats = run_async(
                            SubtitleService.translate_subtitle(
                                input_path=str(asr_subtitle_path),
                                output_path=str(output_path),
                                source_lang=source_lang,
                                target_lang=target_lang,
                                model=model,
                                provider=provider,
                                batch_size=settings.translation_batch_size,
                                preserve_formatting=settings.preserve_ass_styles,
                                enable_proofreading=settings.enable_translation_proofreading,
                                progress_callback=progress_callback,
                                db_session=session,
                                subtitle_id=None,
                                asset_id=asset_id,
                                media_name=media_name,
                            )
                        )

                    result_paths.append(str(output_path))
                    logger.info(f"Translation to {target_lang} completed: {stats}")

                    # Save checkpoint after each language completes
                    with session_scope() as session:
                        save_checkpoint(session, job_id, None, completed_target_lang=target_lang)
                        # Also save result paths progressively
                        job = (
                            session.query(TranslationJob)
                            .filter(TranslationJob.id == job_id)
                            .first()
                        )
                        job.result_paths = json.dumps(result_paths)
                        session.commit()

            # === 5. Writeback to Jellyfin (if item_id present) ===
            if item_id:
                logger.info(f"Job has item_id {item_id}, performing writeback")

                from app.models.media_asset import MediaAsset
                from app.models.subtitle import Subtitle
                from app.services.writeback import WritebackService

                with session_scope() as session:
                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    job.current_phase = "writeback"
                    session.commit()

                run_async(
                    event_publisher.publish_job_progress(
                        job_id=job_id,
                        phase="writeback",
                        status="writing back to Jellyfin",
                        progress=85,
                    )
                )

                # Create subtitle records and writeback
                for output_path, target_lang in zip(result_paths, target_langs, strict=False):
                    with session_scope() as session:
                        # Get or create media asset
                        asset = session.query(MediaAsset).filter_by(item_id=item_id).first()

                        if not asset:
                            logger.warning(
                                f"MediaAsset not found for item_id {item_id}, creating placeholder"
                            )
                            asset = MediaAsset(
                                item_id=item_id,
                                library_id="",
                                name=f"Item {item_id}",
                                type="Unknown",
                            )
                            session.add(asset)
                            session.flush()

                        # Calculate line count and word count
                        try:
                            import pysubs2

                            subs = pysubs2.load(output_path)
                            line_count = len(subs)
                            word_count = sum(len(event.text.split()) for event in subs)
                        except Exception as e:
                            logger.warning(f"Failed to calculate subtitle stats: {e}")
                            line_count = None
                            word_count = None

                        # Check if subtitle already exists (avoid duplicates)
                        existing_subtitle = (
                            session.query(Subtitle)
                            .filter(
                                Subtitle.asset_id == asset.id,
                                Subtitle.lang == target_lang,
                                Subtitle.origin == "mt",
                                Subtitle.source_lang == source_lang,
                            )
                            .first()
                        )

                        if existing_subtitle:
                            logger.info(
                                f"Subtitle already exists for {target_lang}, updating instead of creating duplicate"
                            )
                            existing_subtitle.storage_path = output_path
                            existing_subtitle.line_count = line_count
                            existing_subtitle.word_count = word_count
                            existing_subtitle.updated_at = datetime.now(UTC)
                            subtitle = existing_subtitle
                        else:
                            # Create subtitle record with origin="mt" (machine translated)
                            subtitle = Subtitle(
                                asset_id=asset.id,
                                lang=target_lang,
                                format="srt",
                                storage_path=output_path,
                                origin="mt",  # Mark as machine translated
                                source_lang=source_lang,
                                is_uploaded=False,
                                line_count=line_count,
                                word_count=word_count,
                            )
                            session.add(subtitle)

                        session.commit()

                        # Perform writeback
                        try:
                            result = run_async(
                                WritebackService.writeback_subtitle(
                                    session=session,
                                    subtitle_id=str(subtitle.id),
                                    mode=None,
                                    force=False,
                                )
                            )
                            logger.info(f"Writeback successful for {target_lang}: {result}")
                        except Exception as e:
                            logger.error(f"Writeback failed for {target_lang}: {e}", exc_info=True)

            # === 6. Update job status ===
            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                job.status = "success"
                job.progress = 100.0
                job.finished_at = datetime.utcnow()
                job.current_phase = "completed"
                job.result_paths = json.dumps(result_paths)
                session.commit()

            # Publish completion event
            run_async(
                event_publisher.publish_job_progress(
                    job_id=job_id,
                    phase="completed",
                    status="success",
                    progress=100,
                )
            )

            logger.info(f"ASR + translation completed for job {job_id}")

            return {
                "status": "success",
                "job_id": job_id,
                "result_paths": result_paths,
                "source_language": source_lang,
                "asr_segments": asr_result["num_segments"],
            }

        except Exception as exc:
            logger.error(f"ASR task failed for job {job_id}: {exc}", exc_info=True)

            # Retry on transient failures
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc)

            # Update job status to failed (final attempt)
            try:
                with session_scope() as session:
                    from app.models.translation_job import TranslationJob

                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    if job:
                        job.status = "failed"
                        job.error = str(exc)
                        job.finished_at = datetime.now(UTC)
                        session.commit()
                        logger.info(f"Job {job_id} marked as failed in database")
            except Exception as db_exc:
                logger.error(f"Failed to update job status in database: {db_exc}", exc_info=True)

            raise


# =============================================================================
# Library Scanning Tasks
# =============================================================================


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="app.workers.tasks.scan_library_task",
    max_retries=3,
    default_retry_delay=300,
)
def scan_library_task(
    self, library_id: str = None, required_langs: list[str] = None, force_rescan: bool = False
) -> dict:
    """
    Scan Jellyfin library for missing subtitles and create translation jobs.

    Args:
        library_id: Jellyfin library ID (if None, scan all libraries)
        required_langs: List of required language codes (overrides settings)
        force_rescan: Force rescan even if recently scanned

    Returns:
        dict: Scan results with jobs created count
    """
    logger.info(f"Starting library scan (library={library_id or 'all'})")

    try:
        from app.models.media_asset import MediaAsset, MediaAudioLang, MediaSubtitleLang
        from app.models.translation_job import TranslationJob
        from app.services.detector import LanguageDetector
        from app.services.jellyfin_client import get_jellyfin_client

        jellyfin_client = get_jellyfin_client()
        detector = LanguageDetector()

        # Get required languages
        # 如果调用方提供了 required_langs 参数，使用它
        # 否则从自动翻译规则中推断，如果没有规则则使用默认值
        if required_langs:
            req_langs = required_langs
            logger.info(f"Using provided required languages: {req_langs}")
        else:
            # 使用新的辅助函数从自动翻译规则推断
            from app.core.db import session_scope

            with session_scope() as session:
                req_langs = detector.get_required_langs_from_rules(session)
            logger.info(f"Inferred required languages from auto translation rules: {req_langs}")

        # Get libraries to scan
        if library_id:
            libraries = [{"id": library_id}]
        else:
            all_libs = run_async(jellyfin_client.list_libraries())
            libraries = [{"id": lib.id} for lib in all_libs]

        jobs_created = 0
        items_scanned = 0
        items_with_missing_langs = 0

        for lib in libraries:
            lib_id = lib["id"]
            logger.info(f"Scanning library: {lib_id}")

            # Get all items from library (paginated)
            start_index = 0
            page_size = 100

            while True:
                response = run_async(
                    jellyfin_client.get_library_items(
                        library_id=lib_id,
                        limit=page_size,
                        start_index=start_index,
                        recursive=True,
                        fields=["MediaStreams", "Path", "MediaSources"],
                    )
                )

                items = response.get("Items", [])
                if not items:
                    break

                logger.info(f"Processing {len(items)} items (offset={start_index})")

                for item_data in items:
                    from app.schemas.jellyfin import JellyfinItem

                    try:
                        item = JellyfinItem.model_validate(item_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse item {item_data.get('Id')}: {e}")
                        continue

                    items_scanned += 1

                    # Filter processable items
                    if not detector.should_process_item(item):
                        continue

                    # Detect missing languages
                    missing_langs = detector.detect_missing_languages(item, req_langs)

                    if not missing_langs:
                        continue

                    items_with_missing_langs += 1

                    # Create or update media asset in database
                    with session_scope() as session:
                        asset = session.query(MediaAsset).filter_by(item_id=item.id).first()

                        if not asset:
                            asset = MediaAsset(
                                item_id=item.id,
                                library_id=lib_id,
                                name=item.name,
                                path=item.path,
                                type=item.type,
                                duration_ms=int(item.run_time_ticks / 10000)
                                if item.run_time_ticks
                                else None,
                            )
                            session.add(asset)
                            session.flush()

                        # Update language tables
                        existing_subtitle_langs = detector.extract_subtitle_languages(item)
                        existing_audio_langs = detector.extract_audio_languages(item)

                        # Clear and rebuild subtitle languages
                        session.query(MediaSubtitleLang).filter_by(asset_id=asset.id).delete()
                        for lang in existing_subtitle_langs:
                            sub_lang = MediaSubtitleLang(asset_id=asset.id, lang=lang)
                            session.add(sub_lang)

                        # Clear and rebuild audio languages
                        session.query(MediaAudioLang).filter_by(asset_id=asset.id).delete()
                        for lang in existing_audio_langs:
                            audio_lang = MediaAudioLang(asset_id=asset.id, lang=lang)
                            session.add(audio_lang)

                        session.commit()

                        # Create translation jobs for missing languages
                        for missing_lang in missing_langs:
                            # Check if job already exists (properly handle JSON field)
                            existing_jobs = (
                                session.query(TranslationJob)
                                .filter(
                                    TranslationJob.item_id == item.id,
                                    TranslationJob.status.in_(["queued", "running"]),
                                )
                                .all()
                            )

                            # Check if missing_lang is in any existing job's target_langs
                            job_exists = False
                            for existing_job in existing_jobs:
                                try:
                                    target_langs = json.loads(existing_job.target_langs)
                                    if missing_lang in target_langs:
                                        job_exists = True
                                        break
                                except:
                                    pass

                            if job_exists and not force_rescan:
                                logger.debug(f"Job already exists for {item.id} → {missing_lang}")
                                continue

                            # Infer source language
                            source_lang = detector.infer_primary_language(item)

                            # Determine source type
                            has_subtitles = len(existing_subtitle_langs) > 0
                            source_type = "subtitle" if has_subtitles else "media"

                            # Set source path based on type
                            source_path = None
                            if source_type == "subtitle" and has_subtitles:
                                # For subtitle source, download first available subtitle
                                try:
                                    import tempfile
                                    from pathlib import Path

                                    # Find first subtitle stream
                                    subtitle_index = None
                                    subtitle_format = None

                                    for source in item.media_sources:
                                        for _idx, stream in enumerate(source.media_streams):
                                            if stream.type.lower() == "subtitle":
                                                subtitle_index = stream.index
                                                # Detect format from codec
                                                if stream.codec:
                                                    if stream.codec.lower() in ["srt", "subrip"]:
                                                        subtitle_format = "srt"
                                                    elif stream.codec.lower() in ["ass", "ssa"]:
                                                        subtitle_format = "ass"
                                                    elif stream.codec.lower() in ["vtt", "webvtt"]:
                                                        subtitle_format = "vtt"
                                                    else:
                                                        subtitle_format = "srt"  # Default to srt
                                                else:
                                                    subtitle_format = "srt"
                                                break
                                        if subtitle_index is not None:
                                            break

                                    if subtitle_index is None:
                                        logger.warning(f"No subtitle stream found for {item.id}")
                                        continue

                                    # Download subtitle to temp directory
                                    temp_dir = (
                                        Path(tempfile.gettempdir()) / "fluxcaption" / "subtitles"
                                    )
                                    temp_dir.mkdir(parents=True, exist_ok=True)

                                    subtitle_filename = (
                                        f"{item.id}_{subtitle_index}.{subtitle_format}"
                                    )
                                    subtitle_path = temp_dir / subtitle_filename

                                    # Download subtitle using Jellyfin client
                                    source_path = str(
                                        run_async(
                                            jellyfin_client.download_subtitle(
                                                item.id, subtitle_index, subtitle_path
                                            )
                                        )
                                    )

                                    logger.info(
                                        f"Downloaded subtitle for {item.name} to {source_path}"
                                    )

                                except Exception as e:
                                    logger.warning(
                                        f"Failed to download subtitle for {item.id}: {e}, falling back to ASR"
                                    )
                                    # Fallback to ASR if subtitle download fails
                                    source_type = "media"
                                    source_path = item.path
                                    if not source_path:
                                        logger.warning(
                                            f"No media path found for {item.id}, skipping"
                                        )
                                        continue
                            else:
                                # For media source (ASR), use media file path
                                source_path = item.path
                                if not source_path:
                                    logger.warning(f"No media path found for {item.id}, skipping")
                                    continue

                            # Create job
                            from app.core.settings_helper import get_default_mt_model

                            job = TranslationJob(
                                item_id=item.id,
                                source_type=source_type,
                                source_path=source_path,
                                source_lang=source_lang,
                                target_langs=json.dumps([missing_lang]),
                                model=get_default_mt_model(),
                                status="queued",
                            )
                            session.add(job)
                            session.flush()  # Get job.id without committing

                            logger.info(
                                f"Created job for {item.name}: {source_lang} → {missing_lang}"
                            )
                            jobs_created += 1

                            # Check auto translation rules
                            from app.models.auto_translation_rule import AutoTranslationRule

                            rules = (
                                session.query(AutoTranslationRule)
                                .filter(AutoTranslationRule.enabled)
                                .all()
                            )

                            auto_started = False
                            for rule in rules:
                                # Parse JSON fields
                                library_ids = json.loads(rule.jellyfin_library_ids)
                                target_langs = json.loads(rule.target_langs)

                                # Check library_id match
                                if library_ids and len(library_ids) > 0:
                                    if library_id and library_id not in library_ids:
                                        continue

                                # Check source_lang match
                                if rule.source_lang and rule.source_lang != source_lang:
                                    continue

                                # Check target_langs match
                                if missing_lang not in target_langs:
                                    continue

                                # Rule matched, auto-start if configured
                                if rule.auto_start:
                                    session.commit()  # Commit before dispatching

                                    # Dispatch to Celery
                                    if source_type == "subtitle":
                                        task = translate_subtitle_task.apply_async(
                                            args=[str(job.id)],
                                            queue="translate",
                                            priority=rule.priority,
                                        )
                                    elif source_type in ("audio", "media", "jellyfin"):
                                        task = asr_then_translate_task.apply_async(
                                            args=[str(job.id)],
                                            queue="asr",
                                            priority=rule.priority,
                                        )

                                    job.celery_task_id = task.id
                                    session.commit()

                                    logger.info(f"Auto-started job {job.id} by rule '{rule.name}'")
                                    auto_started = True
                                    break

                            if not auto_started:
                                session.commit()
                                logger.debug(f"Job {job.id} created and waiting for manual trigger")

                # Move to next page
                start_index += page_size
                if start_index >= response.get("TotalRecordCount", 0):
                    break

        logger.info(
            f"Library scan complete: scanned={items_scanned}, "
            f"with_missing={items_with_missing_langs}, jobs_created={jobs_created}"
        )

        return {
            "status": "success",
            "library_id": library_id or "all",
            "items_scanned": items_scanned,
            "items_with_missing_langs": items_with_missing_langs,
            "jobs_created": jobs_created,
        }

    except Exception as exc:
        logger.error(f"Library scan failed: {exc}", exc_info=True)

        # Retry on transient failures
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        raise


# =============================================================================
# Utility Tasks
# =============================================================================


@celery_app.task(name="app.workers.tasks.cleanup_temp_files")
def cleanup_temp_files() -> dict:
    """
    Clean up temporary files older than a threshold or orphaned (job deleted).

    Returns:
        dict: Cleanup results
    """
    logger.info("Starting temporary file cleanup")

    try:
        import re
        import shutil
        from datetime import datetime, timedelta
        from pathlib import Path

        from app.core.config import settings

        temp_dir = Path(settings.temp_dir)
        if not temp_dir.exists():
            logger.info("Temp directory does not exist, nothing to clean")
            return {
                "status": "success",
                "files_deleted": 0,
                "dirs_deleted": 0,
                "space_freed_mb": 0.0,
                "orphaned_cleaned": 0,
            }

        # Get all existing job IDs from database
        with session_scope() as session:
            from app.models.translation_job import TranslationJob

            existing_job_ids = {str(job.id) for job in session.query(TranslationJob.id).all()}

        logger.info(f"Found {len(existing_job_ids)} active jobs in database")

        # Delete files/dirs older than 24 hours OR orphaned
        threshold_time = datetime.now() - timedelta(hours=24)

        files_deleted = 0
        dirs_deleted = 0
        space_freed = 0
        orphaned_cleaned = 0

        # Pattern to extract job ID from directory name (e.g., asr_<job_id>)
        job_id_pattern = re.compile(r"^asr_([0-9a-f\-]{36})$")

        # Special handling for common temp directories
        common_temp_dirs = ["jellyfin_downloads", "subtitles"]

        for item in temp_dir.iterdir():
            try:
                # Skip if not file or directory
                if not (item.is_dir() or item.is_file()):
                    continue

                should_delete = False
                is_orphaned = False

                # Special handling for common temp directories - clean files inside them
                if item.is_dir() and item.name in common_temp_dirs:
                    # Clean old files inside these directories
                    for subitem in item.iterdir():
                        try:
                            if subitem.is_file():
                                mtime = datetime.fromtimestamp(subitem.stat().st_mtime)
                                if mtime < threshold_time:
                                    file_size = subitem.stat().st_size
                                    space_freed += file_size
                                    subitem.unlink()
                                    files_deleted += 1
                                    logger.info(
                                        f"Deleted old file from {item.name}: {subitem.name} "
                                        f"({file_size / 1024 / 1024:.2f} MB)"
                                    )
                        except Exception as e:
                            logger.warning(f"Failed to delete {subitem}: {e}")
                    continue

                # Check if this is an orphaned job directory
                if item.is_dir():
                    match = job_id_pattern.match(item.name)
                    if match:
                        job_id = match.group(1)
                        if job_id not in existing_job_ids:
                            should_delete = True
                            is_orphaned = True
                            logger.info(f"Found orphaned directory: {item.name} (job deleted)")

                # Check modification time
                if not should_delete:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    if mtime < threshold_time:
                        should_delete = True

                if should_delete:
                    if item.is_dir():
                        # Calculate directory size before deletion
                        dir_size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                        space_freed += dir_size

                        # Remove directory
                        shutil.rmtree(item)
                        dirs_deleted += 1
                        if is_orphaned:
                            orphaned_cleaned += 1

                        reason = "orphaned" if is_orphaned else "old"
                        logger.info(
                            f"Deleted {reason} directory: {item.name} "
                            f"({dir_size / 1024 / 1024:.2f} MB)"
                        )
                    else:
                        # Remove file
                        file_size = item.stat().st_size
                        space_freed += file_size
                        item.unlink()
                        files_deleted += 1
                        logger.info(
                            f"Deleted old file: {item.name} ({file_size / 1024 / 1024:.2f} MB)"
                        )

            except Exception as e:
                logger.warning(f"Failed to delete {item}: {e}")
                continue

        result = {
            "status": "success",
            "files_deleted": files_deleted,
            "dirs_deleted": dirs_deleted,
            "orphaned_cleaned": orphaned_cleaned,
            "space_freed_mb": round(space_freed / 1024 / 1024, 2),
        }

        logger.info(
            f"Cleanup complete: {files_deleted} files, {dirs_deleted} dirs "
            f"({orphaned_cleaned} orphaned), {result['space_freed_mb']} MB freed"
        )

        return result

    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}", exc_info=True)
        raise


@celery_app.task(name="app.workers.tasks.health_check_models")
def health_check_models() -> dict:
    """
    Check health of all registered models.

    Returns:
        dict: Health check results
    """
    logger.info("Starting model health check")

    try:
        # TODO: Implement model health check
        # 1. Query all models from registry
        # 2. Check if they're still available in Ollama
        # 3. Update status in database
        # 4. Return summary

        return {
            "status": "success",
            "models_checked": 0,
        }

    except Exception as exc:
        logger.error(f"Model health check failed: {exc}", exc_info=True)
        raise


# =============================================================================
# Subtitle Sync Tasks
# =============================================================================


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="app.workers.tasks.sync_subtitle_task",
    max_retries=3,
    default_retry_delay=60,
)
def sync_subtitle_task(
    self, subtitle_id: str, mode: str = "incremental", paired_subtitle_id: str = None
) -> dict:
    """
    Sync a single subtitle file to translation memory.

    Args:
        subtitle_id: Subtitle ID to sync
        mode: Sync mode ('full', 'incremental', 'skip')
        paired_subtitle_id: Optional paired subtitle ID

    Returns:
        dict: Sync results
    """
    logger.info(f"Starting subtitle sync task for {subtitle_id}")

    try:
        from app.services.subtitle_sync_service import SubtitleSyncService

        with session_scope() as session:
            sync_service = SubtitleSyncService(session)

            sync_record = sync_service.sync_subtitle_to_memory(
                subtitle_id=subtitle_id, mode=mode, paired_subtitle_id=paired_subtitle_id
            )

            return {
                "status": "success",
                "subtitle_id": subtitle_id,
                "sync_record_id": str(sync_record.id),
                "synced_lines": sync_record.synced_lines,
                "skipped_lines": sync_record.skipped_lines,
                "failed_lines": sync_record.failed_lines,
            }

    except Exception as exc:
        logger.error(f"Subtitle sync task failed: {exc}", exc_info=True)

        # Retry on transient failures
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        raise


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="app.workers.tasks.sync_asset_subtitles_task",
    max_retries=2,
    default_retry_delay=120,
)
def sync_asset_subtitles_task(
    self, asset_id: str, mode: str = "incremental", auto_pair: bool = True
) -> dict:
    """
    Sync all subtitles for a media asset.

    Args:
        asset_id: Media asset ID
        mode: Sync mode
        auto_pair: Auto-pair subtitles for translation memory

    Returns:
        dict: Sync results
    """
    logger.info(f"Starting asset subtitle sync task for {asset_id}")

    try:
        from app.services.subtitle_sync_service import SubtitleSyncService

        with session_scope() as session:
            sync_service = SubtitleSyncService(session)

            results = sync_service.sync_asset_subtitles(
                asset_id=asset_id, mode=mode, auto_pair=auto_pair
            )

            logger.info(
                f"Asset subtitle sync completed: {results['synced_subtitles']} synced, "
                f"{results['failed_subtitles']} failed"
            )

            return results

    except Exception as exc:
        logger.error(f"Asset subtitle sync task failed: {exc}", exc_info=True)

        # Retry on transient failures
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        raise


@celery_app.task(name="app.workers.tasks.sync_all_subtitles_task")
def sync_all_subtitles_task(
    mode: str = "incremental", auto_pair: bool = True, limit: int = None
) -> dict:
    """
    Sync all subtitles in the system to translation memory.

    This is typically run as a periodic task to ensure all subtitles
    are synced to translation memory.

    Args:
        mode: Sync mode
        auto_pair: Auto-pair subtitles
        limit: Optional limit on number of assets to process

    Returns:
        dict: Overall sync results
    """
    logger.info("Starting global subtitle sync task")

    try:
        from app.models.media_asset import MediaAsset

        results = {
            "status": "success",
            "total_assets": 0,
            "synced_assets": 0,
            "failed_assets": 0,
            "total_subtitles_synced": 0,
        }

        with session_scope() as session:
            # Get all assets with subtitles
            query = session.query(MediaAsset).join(MediaAsset.subtitles).distinct()

            if limit:
                query = query.limit(limit)

            assets = query.all()
            results["total_assets"] = len(assets)

            logger.info(f"Found {len(assets)} assets with subtitles")

            for asset in assets:
                try:
                    # Dispatch individual asset sync task
                    sync_asset_subtitles_task.apply_async(
                        args=[str(asset.id)],
                        kwargs={"mode": mode, "auto_pair": auto_pair},
                        queue="translate",
                    )

                    # Wait for result (optional, could be async)
                    # result = task_result.get(timeout=300)
                    # results["total_subtitles_synced"] += result.get("synced_subtitles", 0)

                    results["synced_assets"] += 1

                except Exception as e:
                    logger.error(f"Failed to sync asset {asset.id}: {e}")
                    results["failed_assets"] += 1

        logger.info(f"Global subtitle sync completed: {results['synced_assets']} assets processed")

        return results

    except Exception as exc:
        logger.error(f"Global subtitle sync failed: {exc}", exc_info=True)
        raise


# =============================================================================
# Quota & Task Recovery
# =============================================================================


@celery_app.task(name="app.workers.tasks.resume_paused_jobs_task")
def resume_paused_jobs_task() -> dict:
    """
    Check and resume paused jobs that are ready to run.

    This is typically run as a periodic task (every hour or so) to check if
    any paused jobs can be resumed (quota has reset, etc).

    Returns:
        dict: Summary of resumed jobs
    """
    logger.info("Starting paused jobs resume check")

    try:
        from datetime import datetime

        from app.models.translation_job import TranslationJob

        results = {
            "status": "success",
            "paused_jobs_found": 0,
            "jobs_resumed": 0,
            "jobs_still_paused": 0,
            "errors": [],
        }

        with session_scope() as session:
            # Find all paused jobs ready to resume
            now = datetime.now(UTC)

            paused_jobs = (
                session.query(TranslationJob)
                .filter(
                    TranslationJob.status == "paused",
                    TranslationJob.resume_at.isnot(None),
                    TranslationJob.resume_at <= now,  # Only get jobs ready to resume
                )
                .all()
            )

            results["paused_jobs_found"] = len(paused_jobs)
            logger.info(f"Found {len(paused_jobs)} paused jobs ready to resume")

            for job in paused_jobs:
                try:
                    # Use row-level lock to prevent concurrent resume
                    locked_job = (
                        session.query(TranslationJob)
                        .filter(TranslationJob.id == job.id)
                        .with_for_update(skip_locked=True)  # Skip if locked by another process
                        .first()
                    )

                    # Job might be already resumed by another process
                    if not locked_job or locked_job.status != "paused":
                        logger.debug(f"Job {job.id} already processed by another task")
                        continue

                    logger.info(f"Resuming paused job {job.id} (paused reason: {job.pause_reason})")

                    # Reset job status to queued
                    locked_job.status = "queued"
                    locked_job.pause_reason = None
                    locked_job.paused_at = None
                    locked_job.resume_at = None
                    locked_job.error = None
                    locked_job.started_at = None

                    session.commit()

                    # Resubmit to Celery based on source type
                    try:
                        if locked_job.source_type == "subtitle":
                            task = translate_subtitle_task.apply_async(
                                args=[str(locked_job.id)],
                                queue="translate",
                                priority=locked_job.priority,
                            )
                        elif locked_job.source_type == "audio":
                            task = asr_then_translate_task.apply_async(
                                args=[str(locked_job.id)],
                                queue="asr",
                                priority=locked_job.priority,
                            )
                        else:
                            raise ValueError(f"Unknown source type: {locked_job.source_type}")

                        # Update job with Celery task ID
                        locked_job.celery_task_id = task.id
                        session.commit()

                        logger.info(f"Resubmitted job {job.id} as Celery task {task.id}")
                        results["jobs_resumed"] += 1

                    except Exception as celery_error:
                        logger.error(f"Failed to resubmit job {job.id}: {celery_error}")
                        results["errors"].append(f"Job {job.id}: {str(celery_error)}")
                        session.rollback()

                except Exception as job_error:
                    logger.error(f"Error processing job {job.id}: {job_error}", exc_info=True)
                    results["errors"].append(f"Job {job.id}: {str(job_error)}")
                    session.rollback()

        logger.info(
            f"Paused jobs check completed: "
            f"{results['jobs_resumed']} resumed, "
            f"{len(results['errors'])} errors"
        )

        return results

    except Exception as exc:
        logger.error(f"Failed to resume paused jobs: {exc}", exc_info=True)
        return {
            "status": "failed",
            "error": str(exc),
        }


@celery_app.task(name="app.workers.tasks.check_and_pause_quota_limited_jobs")
def check_and_pause_quota_limited_jobs() -> dict:
    """
    Check for jobs that failed due to quota issues and requeue them as paused.

    This task helps recover jobs that might have failed due to temporary quota limits.

    Returns:
        dict: Summary of paused jobs
    """
    logger.info("Checking for quota-limited jobs to pause")

    try:
        from datetime import datetime, timedelta

        from app.models.translation_job import TranslationJob

        results = {
            "status": "success",
            "jobs_checked": 0,
            "jobs_paused": 0,
        }

        with session_scope() as session:
            # Look for failed jobs from last hour with quota-related errors
            one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

            failed_jobs = (
                session.query(TranslationJob)
                .filter(
                    TranslationJob.status == "failed",
                    TranslationJob.error.isnot(None),
                    TranslationJob.created_at >= one_hour_ago,
                )
                .all()
            )

            results["jobs_checked"] = len(failed_jobs)

            for job in failed_jobs:
                # Check if error is quota-related
                error_text = (job.error or "").lower()
                if "quota" in error_text or "exceeded" in error_text:
                    logger.info(f"Pausing quota-failed job {job.id}")

                    # Pause the job instead of leaving it as failed
                    job.status = "paused"
                    job.pause_reason = "quota_exceeded"
                    job.paused_at = datetime.now(UTC)
                    job.resume_at = datetime.now(UTC) + timedelta(days=1)

                    session.commit()

                    results["jobs_paused"] += 1

        logger.info(
            f"Quota-limited jobs check completed: {results['jobs_paused']} jobs paused for recovery"
        )

        return results

    except Exception as exc:
        logger.error(f"Failed to check quota-limited jobs: {exc}", exc_info=True)
        return {
            "status": "failed",
            "error": str(exc),
        }
