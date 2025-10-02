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
from typing import Optional, Callable
from urllib.parse import urljoin

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.jellyfin import (
    JellyfinLibrary,
    JellyfinItem,
    MediaSource,
    MediaStream,
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
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
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
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        files: Optional[dict] = None,
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
                    raise JellyfinAuthError(f"Unauthorized: invalid API key")
                elif response.status_code == 403:
                    raise JellyfinAuthError(f"Forbidden: insufficient permissions")
                elif response.status_code == 404:
                    raise JellyfinNotFoundError(f"Not found: {path}")
                elif response.status_code >= 400:
                    raise JellyfinError(
                        f"HTTP {response.status_code}: {response.text}"
                    )

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
        List all libraries/collections in Jellyfin with item counts.

        Returns:
            List of libraries with populated ChildCount

        Raises:
            JellyfinError: API error
        """
        logger.info("Listing Jellyfin libraries")

        # Get basic library info from VirtualFolders
        response = await self._request_with_retry("GET", "/Library/VirtualFolders")

        libraries = [
            JellyfinLibrary.model_validate(lib) for lib in response
        ]

        # Get user ID for Items API
        try:
            user_id = await self._get_user_id()
            
            # Get item count for each library
            for library in libraries:
                try:
                    # Query Items API with Limit=1 to get TotalRecordCount efficiently
                    items_response = await self._request_with_retry(
                        "GET",
                        f"/Users/{user_id}/Items",
                        params={
                            "ParentId": library.id,
                            "Limit": 1,
                            "Recursive": "true",
                        }
                    )
                    library.item_count = items_response.get("TotalRecordCount", 0)
                except Exception as e:
                    logger.warning(f"Failed to get item count for library {library.name}: {e}")
                    library.item_count = 0
        except Exception as e:
            logger.warning(f"Failed to get user ID, item counts will be 0: {e}")
            # Keep item_count as None or 0

        logger.info(f"Found {len(libraries)} libraries")
        return libraries

    async def get_library_items(
        self,
        library_id: Optional[str] = None,
        limit: int = 100,
        start_index: int = 0,
        recursive: bool = True,
        fields: Optional[list[str]] = None,
        filters: Optional[dict] = None,
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

    async def get_item(self, item_id: str, fields: Optional[list[str]] = None) -> JellyfinItem:
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
        logger.info(
            f"Uploading subtitle to item {item_id}: {language} ({format})"
        )

        # Read subtitle file
        subtitle_file = Path(subtitle_path)
        if not subtitle_file.exists():
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")

        subtitle_content = subtitle_file.read_bytes()

        # Prepare multipart upload
        files = {
            "data": (
                subtitle_file.name,
                subtitle_content,
                "application/octet-stream",
            )
        }

        params = {
            "Language": language,
            "Format": format,
            "IsForced": str(is_forced).lower(),
        }

        response = await self._request_with_retry(
            "POST",
            f"/Videos/{item_id}/Subtitles",
            params=params,
            files=files,
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
            response = await self._request("GET", "/System/Info")
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
                f"Connected to Jellyfin: {response.get('ServerName')} "
                f"v{response.get('Version')}"
            )
            return True
        except Exception as e:
            logger.error(f"Jellyfin connection failed: {e}")
            return False


# =============================================================================
# Singleton Instance
# =============================================================================

# Global client instance (lazy initialization)
_jellyfin_client: Optional[JellyfinClient] = None


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
