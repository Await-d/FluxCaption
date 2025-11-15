"""
Subtitle writeback service.

Handles writing translated subtitles back to Jellyfin via two modes:
- upload: Upload subtitle via Jellyfin API
- sidecar: Write subtitle file next to media file
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.media_asset import MediaAsset
from app.models.subtitle import Subtitle
from app.services.jellyfin_client import JellyfinError, get_jellyfin_client

logger = get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class WritebackError(Exception):
    """Base exception for writeback errors."""

    pass


class WritebackFileNotFoundError(WritebackError):
    """Subtitle file not found."""

    pass


class WritebackPermissionError(WritebackError):
    """Permission denied for sidecar mode."""

    pass


# =============================================================================
# Writeback Service
# =============================================================================


class WritebackService:
    """
    Service for writing subtitles back to Jellyfin.

    Supports two modes:
    - upload: Upload to Jellyfin via API (POST /Items/{id}/Subtitles)
    - sidecar: Write file next to media file (e.g., movie.zh-CN.srt)
    """

    @staticmethod
    async def writeback_subtitle(
        session: Session,
        subtitle_id: str,
        mode: str | None = None,
        force: bool = False,
    ) -> dict:
        """
        Write subtitle back to Jellyfin.

        Args:
            session: Database session
            subtitle_id: Subtitle record ID (UUID)
            mode: Writeback mode ("upload" or "sidecar", defaults to settings)
            force: Force writeback even if already uploaded

        Returns:
            Dict with writeback result:
            {
                "success": True,
                "mode": "upload",
                "destination": "http://...",
                "message": "..."
            }

        Raises:
            WritebackError: Writeback failed
        """
        # Get subtitle record
        subtitle = session.query(Subtitle).filter_by(id=subtitle_id).first()
        if not subtitle:
            raise WritebackError(f"Subtitle not found: {subtitle_id}")

        # Check if already uploaded
        if subtitle.is_uploaded and not force:
            logger.info(f"Subtitle {subtitle_id} already uploaded, skipping")
            return {
                "success": True,
                "mode": subtitle.writeback_mode or "unknown",
                "destination": "N/A",
                "message": "Already uploaded (use force=True to re-upload)",
            }

        # Get associated media asset
        if not subtitle.asset_id:
            raise WritebackError("Subtitle has no associated media asset")

        asset = session.query(MediaAsset).filter_by(id=subtitle.asset_id).first()
        if not asset:
            raise WritebackError(f"Media asset not found: {subtitle.asset_id}")

        # Determine writeback mode
        writeback_mode = mode or settings.writeback_mode

        # Execute writeback based on mode
        if writeback_mode == "upload":
            result = await WritebackService._writeback_upload(subtitle, asset)
        elif writeback_mode == "sidecar":
            result = await WritebackService._writeback_sidecar(subtitle, asset)
        else:
            raise WritebackError(f"Invalid writeback mode: {writeback_mode}")

        # Update subtitle record
        subtitle.is_uploaded = True
        subtitle.uploaded_at = datetime.utcnow()
        subtitle.writeback_mode = writeback_mode
        session.commit()

        logger.info(
            f"Subtitle {subtitle_id} written back successfully "
            f"via {writeback_mode} to {result['destination']}"
        )

        return result

    @staticmethod
    async def _writeback_upload(subtitle: Subtitle, asset: MediaAsset) -> dict:
        """
        Upload subtitle to Jellyfin via API.

        Args:
            subtitle: Subtitle record
            asset: Associated media asset

        Returns:
            Result dict

        Raises:
            WritebackFileNotFoundError: Subtitle file not found
            WritebackError: Upload failed
        """
        logger.info(f"Uploading subtitle {subtitle.id} to Jellyfin item {asset.item_id}")

        # Verify subtitle file exists
        subtitle_path = Path(subtitle.storage_path)
        if not subtitle_path.exists():
            raise WritebackFileNotFoundError(f"Subtitle file not found: {subtitle.storage_path}")

        # Get Jellyfin client
        jellyfin_client = get_jellyfin_client()

        try:
            # Upload subtitle
            await jellyfin_client.upload_subtitle(
                item_id=asset.item_id,
                subtitle_path=str(subtitle_path),
                language=subtitle.lang,
                format=subtitle.format,
                is_forced=False,
                is_default=False,
            )

            # Trigger metadata refresh
            await jellyfin_client.refresh_item(asset.item_id)

            return {
                "success": True,
                "mode": "upload",
                "destination": f"{jellyfin_client.base_url}Items/{asset.item_id}",
                "message": f"Uploaded to Jellyfin item {asset.item_id}",
            }

        except JellyfinError as e:
            logger.error(f"Jellyfin upload failed: {e}")
            raise WritebackError(f"Upload failed: {e}")

    @staticmethod
    async def _writeback_sidecar(subtitle: Subtitle, asset: MediaAsset) -> dict:
        """
        Write subtitle as sidecar file next to media file.

        Args:
            subtitle: Subtitle record
            asset: Associated media asset

        Returns:
            Result dict

        Raises:
            WritebackFileNotFoundError: Subtitle or media file not found
            WritebackPermissionError: Permission denied
            WritebackError: Write failed
        """
        logger.info(f"Writing subtitle {subtitle.id} as sidecar for {asset.name}")

        # Verify subtitle file exists
        subtitle_path = Path(subtitle.storage_path)
        if not subtitle_path.exists():
            raise WritebackFileNotFoundError(f"Subtitle file not found: {subtitle.storage_path}")

        # Get media file path
        if not asset.path:
            raise WritebackError("Media asset has no file path")

        media_path = Path(asset.path)
        if not media_path.exists():
            raise WritebackFileNotFoundError(f"Media file not found: {asset.path}")

        # Construct sidecar path
        # Example: /media/movie.mkv → /media/movie.zh-CN.srt
        sidecar_path = media_path.with_suffix(f".{subtitle.lang}.{subtitle.format}")

        try:
            # Read subtitle content
            subtitle_content = subtitle_path.read_bytes()

            # Write sidecar file
            sidecar_path.write_bytes(subtitle_content)

            logger.info(f"Sidecar subtitle written to {sidecar_path}")

            # Optionally trigger Jellyfin refresh to detect new subtitle
            try:
                jellyfin_client = get_jellyfin_client()
                await jellyfin_client.refresh_item(asset.item_id)
            except Exception as e:
                logger.warning(f"Could not trigger Jellyfin refresh: {e}")

            return {
                "success": True,
                "mode": "sidecar",
                "destination": str(sidecar_path),
                "message": f"Sidecar file written to {sidecar_path}",
            }

        except PermissionError as e:
            logger.error(f"Permission denied writing sidecar: {e}")
            raise WritebackPermissionError(f"Permission denied: {e}")
        except Exception as e:
            logger.error(f"Sidecar write failed: {e}")
            raise WritebackError(f"Write failed: {e}")

    @staticmethod
    async def batch_writeback(
        session: Session,
        subtitle_ids: list[str],
        mode: str | None = None,
        force: bool = False,
    ) -> dict:
        """
        Write back multiple subtitles in batch.

        Args:
            session: Database session
            subtitle_ids: List of subtitle IDs
            mode: Writeback mode
            force: Force writeback

        Returns:
            Summary dict with success/failure counts
        """
        logger.info(f"Batch writeback for {len(subtitle_ids)} subtitles")

        results = {"success": 0, "failed": 0, "errors": []}

        for subtitle_id in subtitle_ids:
            try:
                await WritebackService.writeback_subtitle(
                    session=session,
                    subtitle_id=subtitle_id,
                    mode=mode,
                    force=force,
                )
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"subtitle_id": subtitle_id, "error": str(e)})
                logger.error(f"Writeback failed for {subtitle_id}: {e}")

        logger.info(
            f"Batch writeback complete: {results['success']} succeeded, {results['failed']} failed"
        )

        return results
