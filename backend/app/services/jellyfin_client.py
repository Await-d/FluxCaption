"""
Jellyfin API client for media library integration.

Provides complete integration with Jellyfin server including:
- Library listing and item querying
- Media stream analysis (audio/subtitle languages)
- Subtitle upload via API
- Item metadata retrieval
"""

import base64
from pathlib import Path
from urllib.parse import urljoin

import aiohttp
import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.jellyfin import (
    JellyfinItem,
    JellyfinLibrary,
)

logger = get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class JellyfinError(Exception):
    """Base exception for Jellyfin client errors."""

    pass


class JellyfinAuthError(JellyfinError):
    """Authentication/authorization error."""

    pass


class JellyfinNotFoundError(JellyfinError):
    """Resource not found."""

    pass


class JellyfinConnectionError(JellyfinError):
    """Connection error."""

    pass


# =============================================================================
# Jellyfin Client
# =============================================================================


class JellyfinClient:
    """
    Async HTTP client for Jellyfin API.

    Handles authentication, retries, and proper error handling for all
    Jellyfin operations required by FluxCaption.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ):
        """
        Initialize Jellyfin client.

        Args:
            base_url: Jellyfin server URL (defaults to settings.jellyfin_base_url)
            api_key: Jellyfin API key (defaults to settings.jellyfin_api_key)
            timeout: Request timeout in seconds (defaults to settings.jellyfin_timeout)
            max_retries: Max retry attempts (defaults to settings.jellyfin_max_retries)
        """
        self.base_url = base_url or settings.jellyfin_base_url
        self.api_key = api_key or settings.jellyfin_api_key
        self.timeout = timeout or settings.jellyfin_timeout
        self.max_retries = max_retries or settings.jellyfin_max_retries

        if not self.base_url:
            raise ValueError("Jellyfin base URL is required")
        if not self.api_key:
            raise ValueError("Jellyfin API key is required")

        # Ensure base URL ends with /
        if not self.base_url.endswith("/"):
            self.base_url += "/"

        logger.info(f"Initialized Jellyfin client for {self.base_url}")

    def _get_headers(self) -> dict:
        """Get request headers with authentication."""
        return {
            "X-MediaBrowser-Token": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        # Remove leading slash if present
        if path.startswith("/"):
            path = path[1:]
        return urljoin(self.base_url, path)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        data: dict | None = None,
        json: dict | None = None,
        files: dict | None = None,
    ) -> dict:
        """
        Make HTTP request to Jellyfin API with retries.

        Args:
            method: HTTP method
            path: API endpoint path
            params: Query parameters
            data: Form data
            json: JSON body
            files: Multipart files

        Returns:
            Response JSON

        Raises:
            JellyfinAuthError: 401/403 errors
            JellyfinNotFoundError: 404 errors
            JellyfinConnectionError: Connection failures
            JellyfinError: Other errors
        """
        url = self._build_url(path)
        headers = self._get_headers()

        # Remove Content-Type for multipart
        if files:
            headers.pop("Content-Type", None)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json,
                    files=files,
                    headers=headers,
                )

                # Handle errors
                if response.status_code == 401:
                    raise JellyfinAuthError("Unauthorized: invalid API key")
                elif response.status_code == 403:
                    raise JellyfinAuthError("Forbidden: insufficient permissions")
                elif response.status_code == 404:
                    raise JellyfinNotFoundError(f"Not found: {path}")
                elif response.status_code >= 400:
                    raise JellyfinError(f"HTTP {response.status_code}: {response.text}")

                # Return JSON response (empty dict if no content)
                if response.status_code == 204 or not response.content:
                    return {}

                return response.json()

        except httpx.ConnectError as e:
            raise JellyfinConnectionError(f"Connection failed: {e}")
        except httpx.TimeoutException as e:
            raise JellyfinConnectionError(f"Request timeout: {e}")
        except (JellyfinAuthError, JellyfinNotFoundError, JellyfinError):
            raise
        except Exception as e:
            raise JellyfinError(f"Request failed: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(JellyfinConnectionError),
        reraise=True,
    )
    async def _request_with_retry(self, *args, **kwargs) -> dict:
        """Make request with automatic retries for connection errors."""
        return await self._request(*args, **kwargs)

    # =========================================================================
    # Library Operations
    # =========================================================================

    async def list_libraries(self) -> list[JellyfinLibrary]:
        """
        List all libraries/collections in Jellyfin with item counts and image tags.

        For libraries without a primary image, uses the first item's image as fallback.

        Returns:
            List of libraries with populated ChildCount and ImageTags

        Raises:
            JellyfinError: API error
        """
        logger.info("Listing Jellyfin libraries")

        # Get basic library info from VirtualFolders
        response = await self._request_with_retry("GET", "/Library/VirtualFolders")

        libraries = [JellyfinLibrary.model_validate(lib) for lib in response]

        # Get user ID for Items API
        try:
            user_id = await self._get_user_id()

            # Get detailed info for each library including ImageTags
            for library in libraries:
                try:
                    # Get library item details to fetch ImageTags
                    library_item = await self._request_with_retry(
                        "GET",
                        f"/Users/{user_id}/Items/{library.id}",
                    )

                    # Extract ImageTags from the library item
                    if "ImageTags" in library_item and library_item["ImageTags"]:
                        library.image_tags = library_item.get("ImageTags")
                        library.image_item_id = library.id  # Use library's own ID

                    # Query Items API with Limit=1 to get TotalRecordCount efficiently
                    items_response = await self._request_with_retry(
                        "GET",
                        f"/Users/{user_id}/Items",
                        params={
                            "ParentId": library.id,
                            "Limit": 1,
                            "Recursive": "true",
                        },
                    )
                    library.item_count = items_response.get("TotalRecordCount", 0)

                    # If library doesn't have a Primary image, try to get first item's image
                    if not library.image_tags or "Primary" not in library.image_tags:
                        items = items_response.get("Items", [])
                        if items and len(items) > 0:
                            first_item = items[0]
                            # Use first item's ImageTags if available
                            if "ImageTags" in first_item and first_item["ImageTags"]:
                                library.image_tags = first_item.get("ImageTags")
                                library.image_item_id = first_item.get("Id")  # Use first item's ID
                                logger.info(f"Using first item's image for library {library.name}")

                except Exception as e:
                    logger.warning(f"Failed to get details for library {library.name}: {e}")
                    library.item_count = 0
                    library.image_tags = None
                    library.image_item_id = None
        except Exception as e:
            logger.warning(
                f"Failed to get user ID, item counts and images will be unavailable: {e}"
            )
            # Keep item_count as None or 0

        logger.info(f"Found {len(libraries)} libraries")
        return libraries

    async def get_library_items(
        self,
        library_id: str | None = None,
        limit: int = 100,
        start_index: int = 0,
        recursive: bool = True,
        fields: list[str] | None = None,
        filters: dict | None = None,
    ) -> dict:
        """
        Get items from a library with pagination.

        Args:
            library_id: Parent library ID (if None, get all items)
            limit: Max results per page
            start_index: Offset for pagination
            recursive: Include nested items
            fields: Additional fields to include (e.g., ["MediaStreams", "Path"])
            filters: Additional filters

        Returns:
            Dict with 'Items' and 'TotalRecordCount' keys

        Raises:
            JellyfinError: API error
        """
        logger.info(
            f"Getting library items (library={library_id}, limit={limit}, start={start_index})"
        )

        params = {
            "Limit": limit,
            "StartIndex": start_index,
            "Recursive": recursive,
        }

        if library_id:
            params["ParentId"] = library_id

        if fields:
            params["Fields"] = ",".join(fields)

        if filters:
            params.update(filters)

        response = await self._request_with_retry("GET", "/Items", params=params)

        total = response.get("TotalRecordCount", 0)
        items = response.get("Items", [])

        logger.info(f"Retrieved {len(items)} items (total: {total})")
        return response

    async def get_item(self, item_id: str, fields: list[str] | None = None) -> JellyfinItem:
        """
        Get detailed information about a specific item.

        Args:
            item_id: Jellyfin item ID
            fields: Additional fields to include

        Returns:
            Item details

        Raises:
            JellyfinNotFoundError: Item not found
            JellyfinError: API error
        """
        logger.info(f"Getting item details: {item_id}")

        params = {}
        if fields:
            params["Fields"] = ",".join(fields)

        response = await self._request_with_retry(
            "GET", f"/Users/{await self._get_user_id()}/Items/{item_id}", params=params
        )

        item = JellyfinItem.model_validate(response)
        logger.info(f"Retrieved item: {item.name} ({item.type})")
        return item

    async def download_item(self, item_id: str, output_path: Path) -> Path:
        """
        Download media file from Jellyfin.

        Args:
            item_id: Jellyfin item ID
            output_path: Path to save the downloaded file

        Returns:
            Path: Path to the downloaded file

        Raises:
            JellyfinError: If download fails
        """
        logger.info(f"Downloading item {item_id} from Jellyfin")

        url = self._build_url(f"Items/{item_id}/Download")
        headers = self._get_headers()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=3600)
                ) as response:
                    if response.status == 404:
                        raise JellyfinNotFoundError(f"Item {item_id} not found")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise JellyfinError(f"Failed to download item: {error_text}")

                    # Create output directory if needed
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Download file in chunks
                    total_size = int(response.headers.get("content-length", 0))
                    downloaded = 0

                    with open(output_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if (
                                total_size > 0 and downloaded % (10 * 1024 * 1024) == 0
                            ):  # Log every 10MB
                                progress = (downloaded / total_size) * 100
                                logger.info(f"Download progress: {progress:.1f}%")

                    logger.info(f"Downloaded {item_id} to {output_path} ({downloaded} bytes)")
                    return output_path

        except aiohttp.ClientError as e:
            raise JellyfinConnectionError(f"Failed to download item: {e}")

    async def download_subtitle(
        self,
        item_id: str,
        subtitle_index: int,
        output_path: Path,
    ) -> Path:
        """
        Download subtitle file from Jellyfin.

        Args:
            item_id: Jellyfin item ID
            subtitle_index: Index of subtitle stream in MediaStreams
            output_path: Path to save the downloaded subtitle file

        Returns:
            Path: Path to the downloaded subtitle file

        Raises:
            JellyfinError: If download fails
        """
        logger.info(f"Downloading subtitle {subtitle_index} for item {item_id}")

        url = self._build_url(f"Videos/{item_id}/Subtitles/{subtitle_index}/Stream")
        headers = self._get_headers()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status == 404:
                        raise JellyfinNotFoundError(
                            f"Subtitle {subtitle_index} not found for item {item_id}"
                        )
                    elif response.status != 200:
                        error_text = await response.text()
                        raise JellyfinError(f"Failed to download subtitle: {error_text}")

                    # Create output directory if needed
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Download subtitle content
                    content = await response.read()

                    with open(output_path, "wb") as f:
                        f.write(content)

                    logger.info(f"Downloaded subtitle to {output_path} ({len(content)} bytes)")
                    return output_path

        except aiohttp.ClientError as e:
            raise JellyfinConnectionError(f"Failed to download subtitle: {e}")

    # =========================================================================
    # Subtitle Operations
    # =========================================================================

    async def upload_subtitle(
        self,
        item_id: str,
        subtitle_path: str,
        language: str,
        format: str,
        is_forced: bool = False,
        is_default: bool = False,
    ) -> dict:
        """
        Upload subtitle to Jellyfin item via API.

        Args:
            item_id: Target item ID
            subtitle_path: Path to subtitle file
            language: BCP-47 language code
            format: Subtitle format (srt, ass, vtt)
            is_forced: Whether this is a forced subtitle
            is_default: Whether this should be default

        Returns:
            API response

        Raises:
            FileNotFoundError: Subtitle file not found
            JellyfinError: Upload failed
        """
        logger.info(f"Uploading subtitle to item {item_id}: {language} ({format})")

        # Read subtitle file
        subtitle_file = Path(subtitle_path)
        if not subtitle_file.exists():
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")

        subtitle_content = subtitle_file.read_bytes()

        # Jellyfin expects JSON payload with Base64-encoded subtitle data
        encoded_data = base64.b64encode(subtitle_content).decode("utf-8")

        payload = {
            "Language": language,
            "Format": format,
            "IsForced": is_forced,
            "Data": encoded_data,
        }

        response = await self._request_with_retry(
            "POST",
            f"/Videos/{item_id}/Subtitles",
            json=payload,
        )

        logger.info(f"Subtitle uploaded successfully to item {item_id}")
        return response

    async def delete_subtitle(self, item_id: str, subtitle_index: int) -> dict:
        """
        Delete subtitle from Jellyfin item.

        Args:
            item_id: Item ID
            subtitle_index: Index of subtitle to delete

        Returns:
            API response
        """
        logger.info(f"Deleting subtitle {subtitle_index} from item {item_id}")

        response = await self._request_with_retry(
            "DELETE",
            f"/Videos/{item_id}/Subtitles/{subtitle_index}",
        )

        logger.info("Subtitle deleted successfully")
        return response

    async def get_audio_stream_url(
        self,
        item_id: str,
        max_bitrate: int = 320000,
        audio_codec: str = "aac",
        container: str = "mp4",
    ) -> str:
        """
        Get audio stream URL for direct FFmpeg processing.

        This endpoint allows streaming audio directly to FFmpeg without
        downloading the entire video file, significantly reducing bandwidth
        and storage requirements.

        Args:
            item_id: Jellyfin item ID
            max_bitrate: Maximum audio bitrate (default: 320kbps)
            audio_codec: Audio codec for transcoding (default: aac)
            container: Container format (default: mp4)

        Returns:
            Full URL to audio stream with authentication

        Example:
            url = await client.get_audio_stream_url("abc123")
            # FFmpeg can now extract from this URL:
            # ffmpeg -i "url" -vn -acodec pcm_s16le output.wav
        """
        logger.info(f"Getting audio stream URL for item {item_id}")

        # Build streaming URL with parameters
        # Use /stream endpoint which provides direct HTTP streaming suitable for FFmpeg
        params = {
            "Container": container,
            "AudioCodec": audio_codec,
            "AudioBitrate": max_bitrate,
            "api_key": self.api_key,
        }

        # Build URL with query parameters
        base_stream_url = self._build_url(f"Audio/{item_id}/stream")

        # Add query parameters
        from urllib.parse import urlencode

        query_string = urlencode(params)
        stream_url = f"{base_stream_url}?{query_string}"

        logger.info(f"Audio stream URL generated for item {item_id}")
        return stream_url

    # =========================================================================
    # Library Refresh
    # =========================================================================

    async def refresh_item(self, item_id: str) -> dict:
        """
        Trigger metadata refresh for an item.

        Useful after uploading subtitles to ensure Jellyfin detects them.

        Args:
            item_id: Item ID to refresh

        Returns:
            API response
        """
        logger.info(f"Refreshing item metadata: {item_id}")

        response = await self._request_with_retry(
            "POST",
            f"/Items/{item_id}/Refresh",
            params={"Recursive": "false", "MetadataRefreshMode": "Default"},
        )

        logger.info("Item refresh triggered")
        return response

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_user_id(self) -> str:
        """
        Get user ID for API key (required for some endpoints).

        Returns:
            User ID

        Raises:
            JellyfinError: Cannot get user ID
        """
        # For API key auth, we can use any valid user ID
        # Try to get current user from /System/Info
        try:
            await self._request("GET", "/System/Info")
            # API key doesn't have a specific user, use admin user
            # We'll query users and pick first admin
            users_response = await self._request("GET", "/Users")
            for user in users_response:
                if user.get("Policy", {}).get("IsAdministrator"):
                    return user["Id"]
            # Fallback: use first user
            if users_response:
                return users_response[0]["Id"]
            raise JellyfinError("No users found")
        except Exception as e:
            logger.warning(f"Could not get user ID, using empty string: {e}")
            return ""

    async def check_connection(self) -> bool:
        """
        Test connection to Jellyfin server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = await self._request("GET", "/System/Info")
            logger.info(
                f"Connected to Jellyfin: {response.get('ServerName')} v{response.get('Version')}"
            )
            return True
        except Exception as e:
            logger.error(f"Jellyfin connection failed: {e}")
            return False


# =============================================================================
# Singleton Instance
# =============================================================================

# Global client instance (lazy initialization)
_jellyfin_client: JellyfinClient | None = None


def get_jellyfin_client() -> JellyfinClient:
    """
    Get global Jellyfin client instance.

    Returns:
        Shared JellyfinClient instance
    """
    global _jellyfin_client
    if _jellyfin_client is None:
        _jellyfin_client = JellyfinClient()
    return _jellyfin_client
