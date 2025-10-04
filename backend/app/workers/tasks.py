"""
Celery tasks for background processing.

Defines tasks for translation, ASR, and library scanning.
"""

import json
import traceback
import asyncio
from datetime import datetime
from pathlib import Path
from celery import Task
from app.workers.celery_app import celery_app
from app.core.logging import get_logger, JobLogContext
from app.core.db import session_scope
from app.core.events import event_publisher
from app.core.config import settings

logger = get_logger(__name__)


# Helper to run async code in sync context
def run_async(coro):
    """Run an async coroutine in a synchronous context."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


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
                        from app.models.translation_job import TranslationJob
                        from datetime import datetime, timezone

                        job = session.query(TranslationJob).filter(
                            TranslationJob.id == job_id
                        ).first()

                        if job and job.status == "running":
                            job.status = "failed"
                            if not job.error:
                                job.error = str(exc)
                            if not job.finished_at:
                                job.finished_at = datetime.now(timezone.utc)
                            session.commit()
                            logger.info(f"Job {job_id} status updated to failed in on_failure handler")
        except Exception as db_exc:
            logger.error(f"Failed to update job status in on_failure handler: {db_exc}", exc_info=True)

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
    from app.core.config import settings
    
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
            item_id = job.item_id  # Extract item_id for writeback

            # === 2. Ensure model is available ===
            from app.services.ollama_client import ollama_client

            logger.info(f"Checking model availability: {model}")
            job.current_phase = "model_check"

            model_exists = run_async(ollama_client.check_model_exists(model))

            if not model_exists:
                logger.info(f"Model {model} not found locally, pulling...")
                job.current_phase = "pull"

                # Publish pull start event
                run_async(event_publisher.publish_job_progress(
                    job_id=job_id,
                    phase="pull",
                    status="pulling",
                    progress=0,
                ))

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
                        run_async(event_publisher.publish_job_progress(
                            job_id=job_id,
                            phase="pull",
                            status=status_msg,
                            progress=progress_pct,
                            completed=completed,
                            total=total,
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to publish progress: {e}")

                run_async(ollama_client.pull_model(model, progress_callback=pull_progress_callback))
                logger.info(f"Model {model} pulled successfully")

            # === 3. Load and translate subtitle ===
            from app.services.subtitle_service import SubtitleService

            if not source_path or not Path(source_path).exists():
                raise FileNotFoundError(f"Source subtitle file not found: {source_path}")

            output_dir = Path(settings.subtitle_output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            result_paths = []
            total_targets = len(target_langs)

            for idx, target_lang in enumerate(target_langs):
                logger.info(f"Translating to {target_lang} ({idx+1}/{total_targets})")

                with session_scope() as session:
                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    job.current_phase = "mt"
                    session.commit()

                # Build output path
                source_file = Path(source_path)
                output_path = output_dir / f"{source_file.stem}_{target_lang}{source_file.suffix}"

                # Progress callback for translation
                def progress_callback(completed: int, total: int, message: str = ""):
                    progress_pct = (completed / total) * 100
                    base_progress = (idx / total_targets) * 100
                    current_progress = base_progress + (progress_pct / total_targets)

                    # Use message if provided, otherwise use default
                    status_msg = message if message else f"Translating to {target_lang}"

                    # Publish progress
                    try:
                        run_async(event_publisher.publish_job_progress(
                            job_id=job_id,
                            phase="mt",
                            status=status_msg,
                            progress=current_progress,
                            completed=completed,
                            total=total,
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to publish progress: {e}")

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
                    stats = run_async(SubtitleService.translate_subtitle(
                        input_path=str(source_path),
                        output_path=str(output_path),
                        source_lang=source_lang,
                        target_lang=target_lang,
                        model=model,
                        batch_size=settings.translation_batch_size,
                        preserve_formatting=settings.preserve_ass_styles,
                        progress_callback=progress_callback,
                        db_session=session,
                        subtitle_id=None,
                        asset_id=asset_id,
                        media_name=media_name,
                    ))

                result_paths.append(str(output_path))
                logger.info(f"Translation to {target_lang} completed: {stats}")

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

                run_async(event_publisher.publish_job_progress(
                    job_id=job_id,
                    phase="writeback",
                    status="writing back to Jellyfin",
                    progress=95,
                ))

                # Create subtitle records and writeback
                for idx, (output_path, target_lang) in enumerate(zip(result_paths, target_langs)):
                    with session_scope() as session:
                        # Get or create media asset
                        asset = session.query(MediaAsset).filter_by(item_id=item_id).first()

                        if not asset:
                            logger.warning(f"MediaAsset not found for item_id {item_id}, creating placeholder")
                            asset = MediaAsset(
                                item_id=item_id,
                                library_id="",
                                name=f"Item {item_id}",
                                type="Unknown"
                            )
                            session.add(asset)
                            session.flush()

                        # Create subtitle record
                        subtitle = Subtitle(
                            asset_id=asset.id,
                            lang=target_lang,
                            format=Path(output_path).suffix.lstrip('.'),
                            storage_path=output_path,
                            origin="mt",
                            source_lang=source_lang,
                            is_uploaded=False,
                        )
                        session.add(subtitle)
                        session.commit()

                        # Perform writeback
                        try:
                            result = run_async(WritebackService.writeback_subtitle(
                                session=session,
                                subtitle_id=str(subtitle.id),
                                mode=None,  # Use default from settings
                                force=False,
                            ))
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
            run_async(event_publisher.publish_job_progress(
                job_id=job_id,
                phase="completed",
                status="success",
                progress=100,
            ))

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
    from app.core.config import settings
    from datetime import datetime, timezone
    
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
                job.started_at = datetime.now(timezone.utc)
                job.current_phase = "init"
                session.commit()

                # Extract job data
                source_path = job.source_path  # Path to media file
                source_lang = job.source_lang
                target_langs = json.loads(job.target_langs)
                model = job.model
                item_id = job.item_id

            # If source_path doesn't exist or is None, and we have item_id (Jellyfin), use audio streaming
            if item_id and (not source_path or not Path(source_path).exists()):
                if source_path:
                    logger.info(f"Source path {source_path} not accessible, using Jellyfin audio stream for item {item_id}")
                else:
                    logger.info(f"No source path provided, using Jellyfin audio stream for item {item_id}")

                from app.services.jellyfin_client import get_jellyfin_client
                jellyfin = get_jellyfin_client()

                # Get audio stream URL instead of downloading entire file
                try:
                    audio_stream_url = run_async(jellyfin.get_audio_stream_url(item_id))
                    source_path = audio_stream_url  # Use URL directly as source
                    logger.info(f"Using Jellyfin audio stream URL for extraction")

                    # Update job with stream URL
                    with session_scope() as session:
                        job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
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

            # === 2. Extract audio from media ===
            from app.services.audio_extractor import AudioExtractor

            logger.info(f"Extracting audio from {source_path}")

            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                job.current_phase = "extract"
                session.commit()

            run_async(event_publisher.publish_job_progress(
                job_id=job_id,
                phase="extract",
                status="extracting audio",
                progress=5,
            ))

            # Create temp directory for audio
            audio_temp_dir = Path(settings.temp_dir) / f"asr_{job_id}"
            audio_temp_dir.mkdir(parents=True, exist_ok=True)
            audio_path = audio_temp_dir / "audio.wav"

            extractor = AudioExtractor()

            def extract_progress_callback(progress: float):
                try:
                    run_async(event_publisher.publish_job_progress(
                        job_id=job_id,
                        phase="extract",
                        status="extracting audio",
                        progress=5 + (progress * 0.15),  # 5-20%
                    ))
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

            # === 3. Perform ASR (faster-whisper) ===
            from app.services.asr_service import get_asr_service

            logger.info("Starting ASR transcription")

            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                job.current_phase = "asr"
                session.commit()

            run_async(event_publisher.publish_job_progress(
                job_id=job_id,
                phase="asr",
                status="transcribing audio",
                progress=20,
            ))

            asr_service = get_asr_service()

            # Determine ASR language
            asr_lang = None if source_lang == "auto" else source_lang

            def asr_progress_callback(completed: int, total: int):
                try:
                    if total > 0:
                        progress_pct = 20 + (completed / total) * 30  # 20-50%
                    else:
                        progress_pct = 20
                    run_async(event_publisher.publish_job_progress(
                        job_id=job_id,
                        phase="asr",
                        status=f"transcribing ({completed} segments)",
                        progress=progress_pct,
                        completed=completed,
                        total=total,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to publish ASR progress: {e}")

            # Create output directory for ASR subtitle
            asr_output_dir = Path(settings.subtitle_output_dir) / "asr"
            asr_output_dir.mkdir(parents=True, exist_ok=True)
            asr_subtitle_path = asr_output_dir / f"{job_id}_original.srt"

            asr_result = asr_service.transcribe_to_srt(
                audio_path=str(audio_path),
                output_path=str(asr_subtitle_path),
                language=asr_lang,
                vad_filter=settings.asr_vad_filter,
                vad_threshold=settings.asr_vad_threshold,
                beam_size=settings.asr_beam_size,
                best_of=settings.asr_best_of,
                progress_callback=asr_progress_callback,
            )

            logger.info(
                f"ASR complete: {asr_result['num_segments']} segments, "
                f"language={asr_result['language']}"
            )

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
                    logger.warning(f"MediaAsset not found for item_id {item_id}, creating placeholder")
                    asset = MediaAsset(
                        item_id=item_id,
                        library_id="",
                        name=f"Item {item_id}",
                        type="Unknown"
                    )
                    session.add(asset)
                    session.flush()

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
                )
                session.add(asr_source_subtitle)
                session.commit()
                logger.info(f"Saved ASR source subtitle to database: {source_lang}, {asr_result.get('num_segments', 0)} segments")

            # Clean up audio file
            audio_path.unlink(missing_ok=True)

            # === 4. Translate generated subtitle ===
            from app.services.subtitle_service import SubtitleService

            logger.info("Starting translation of ASR-generated subtitle")

            with session_scope() as session:
                job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                job.current_phase = "mt"
                job.source_lang = source_lang  # Update with detected language
                session.commit()

            output_dir = Path(settings.subtitle_output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            result_paths = []
            total_targets = len(target_langs)

            for idx, target_lang in enumerate(target_langs):
                logger.info(f"Translating to {target_lang} ({idx+1}/{total_targets})")

                # Build output path
                source_file = Path(asr_subtitle_path)
                output_path = output_dir / f"{source_file.stem}_{target_lang}.srt"

                # Progress callback for translation
                def progress_callback(completed: int, total: int, message: str = ""):
                    base_progress = 50 + (idx / total_targets) * 30
                    if total > 0:
                        current_progress = base_progress + ((completed / total) * (30 / total_targets))
                    else:
                        current_progress = base_progress

                    # Use message if provided, otherwise use default
                    status_msg = message if message else f"Translating to {target_lang}"

                    try:
                        run_async(event_publisher.publish_job_progress(
                            job_id=job_id,
                            phase="mt",
                            status=status_msg,
                            progress=current_progress,
                            completed=completed,
                            total=total,
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to publish translation progress: {e}")

                # Perform translation
                stats = run_async(SubtitleService.translate_subtitle(
                    input_path=str(asr_subtitle_path),
                    output_path=str(output_path),
                    source_lang=source_lang,
                    target_lang=target_lang,
                    model=model,
                    batch_size=settings.translation_batch_size,
                    preserve_formatting=settings.preserve_ass_styles,
                    progress_callback=progress_callback,
                ))

                result_paths.append(str(output_path))
                logger.info(f"Translation to {target_lang} completed: {stats}")

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

                run_async(event_publisher.publish_job_progress(
                    job_id=job_id,
                    phase="writeback",
                    status="writing back to Jellyfin",
                    progress=85,
                ))

                # Create subtitle records and writeback
                for output_path, target_lang in zip(result_paths, target_langs):
                    with session_scope() as session:
                        # Get or create media asset
                        asset = session.query(MediaAsset).filter_by(item_id=item_id).first()

                        if not asset:
                            logger.warning(f"MediaAsset not found for item_id {item_id}, creating placeholder")
                            asset = MediaAsset(
                                item_id=item_id,
                                library_id="",
                                name=f"Item {item_id}",
                                type="Unknown"
                            )
                            session.add(asset)
                            session.flush()

                        # Create subtitle record with origin="mt" (machine translated)
                        subtitle = Subtitle(
                            asset_id=asset.id,
                            lang=target_lang,
                            format="srt",
                            storage_path=output_path,
                            origin="mt",  # Mark as machine translated
                            source_lang=source_lang,
                            is_uploaded=False,
                        )
                        session.add(subtitle)
                        session.commit()

                        # Perform writeback
                        try:
                            result = run_async(WritebackService.writeback_subtitle(
                                session=session,
                                subtitle_id=str(subtitle.id),
                                mode=None,
                                force=False,
                            ))
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
            run_async(event_publisher.publish_job_progress(
                job_id=job_id,
                phase="completed",
                status="success",
                progress=100,
            ))

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
                        job.finished_at = datetime.now(timezone.utc)
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
    self,
    library_id: str = None,
    required_langs: list[str] = None,
    force_rescan: bool = False
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
        from app.services.jellyfin_client import get_jellyfin_client
        from app.services.detector import LanguageDetector
        from app.models.translation_job import TranslationJob
        from app.models.media_asset import MediaAsset, MediaSubtitleLang, MediaAudioLang
        from app.models.subtitle import Subtitle

        jellyfin_client = get_jellyfin_client()
        detector = LanguageDetector()

        # Get required languages
        req_langs = required_langs or settings.required_langs.split(",")
        logger.info(f"Required languages: {req_langs}")

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
                response = run_async(jellyfin_client.get_library_items(
                    library_id=lib_id,
                    limit=page_size,
                    start_index=start_index,
                    recursive=True,
                    fields=["MediaStreams", "Path", "MediaSources"],
                ))

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
                                duration_ms=int(item.run_time_ticks / 10000) if item.run_time_ticks else None,
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
                            existing_jobs = session.query(TranslationJob).filter(
                                TranslationJob.item_id == item.id,
                                TranslationJob.status.in_(["queued", "running"])
                            ).all()
                            
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
                                        for idx, stream in enumerate(source.media_streams):
                                            if stream.type.lower() == "subtitle":
                                                subtitle_index = stream.index
                                                # Detect format from codec
                                                if stream.codec:
                                                    if stream.codec.lower() in ['srt', 'subrip']:
                                                        subtitle_format = 'srt'
                                                    elif stream.codec.lower() in ['ass', 'ssa']:
                                                        subtitle_format = 'ass'
                                                    elif stream.codec.lower() in ['vtt', 'webvtt']:
                                                        subtitle_format = 'vtt'
                                                    else:
                                                        subtitle_format = 'srt'  # Default to srt
                                                else:
                                                    subtitle_format = 'srt'
                                                break
                                        if subtitle_index is not None:
                                            break
                                    
                                    if subtitle_index is None:
                                        logger.warning(f"No subtitle stream found for {item.id}")
                                        continue
                                    
                                    # Download subtitle to temp directory
                                    temp_dir = Path(tempfile.gettempdir()) / "fluxcaption" / "subtitles"
                                    temp_dir.mkdir(parents=True, exist_ok=True)
                                    
                                    subtitle_filename = f"{item.id}_{subtitle_index}.{subtitle_format}"
                                    subtitle_path = temp_dir / subtitle_filename
                                    
                                    # Download subtitle using Jellyfin client
                                    source_path = str(run_async(
                                        jellyfin_client.download_subtitle(
                                            item.id,
                                            subtitle_index,
                                            subtitle_path
                                        )
                                    ))
                                    
                                    logger.info(f"Downloaded subtitle for {item.name} to {source_path}")
                                    
                                except Exception as e:
                                    logger.warning(f"Failed to download subtitle for {item.id}: {e}, falling back to ASR")
                                    # Fallback to ASR if subtitle download fails
                                    source_type = "media"
                                    source_path = item.path
                                    if not source_path:
                                        logger.warning(f"No media path found for {item.id}, skipping")
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

                            logger.info(f"Created job for {item.name}: {source_lang} → {missing_lang}")
                            jobs_created += 1

                            # Check auto translation rules
                            from app.models.auto_translation_rule import AutoTranslationRule

                            rules = session.query(AutoTranslationRule).filter(
                                AutoTranslationRule.enabled == True
                            ).all()

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
        from pathlib import Path
        from datetime import datetime, timedelta
        import shutil
        import re
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
            existing_job_ids = {
                str(job.id) 
                for job in session.query(TranslationJob.id).all()
            }
        
        logger.info(f"Found {len(existing_job_ids)} active jobs in database")
        
        # Delete files/dirs older than 24 hours OR orphaned
        threshold_time = datetime.now() - timedelta(hours=24)
        
        files_deleted = 0
        dirs_deleted = 0
        space_freed = 0
        orphaned_cleaned = 0
        
        # Pattern to extract job ID from directory name (e.g., asr_<job_id>)
        job_id_pattern = re.compile(r'^asr_([0-9a-f\-]{36})$')
        
        # Special handling for common temp directories
        common_temp_dirs = ['jellyfin_downloads', 'subtitles']
        
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
                        dir_size = sum(
                            f.stat().st_size 
                            for f in item.rglob('*') 
                            if f.is_file()
                        )
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
                            f"Deleted old file: {item.name} "
                            f"({file_size / 1024 / 1024:.2f} MB)"
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
