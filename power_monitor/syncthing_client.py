"""
Syncthing REST API client for pausing and resuming sync operations.

This module provides a thread-safe client for interacting with the Syncthing REST API
to pause and resume the local device's sync operations.
"""

import logging
import threading
from typing import Optional

import requests


class SyncthingError(Exception):
    """Base exception for Syncthing client errors."""


class SyncthingConnectionError(SyncthingError):
    """Raised when connection to Syncthing API fails."""


class SyncthingAPIError(SyncthingError):
    """Raised when Syncthing API returns an error."""


class SyncthingClient:
    """
    Thread-safe client for interacting with Syncthing REST API.

    This client connects to a local Syncthing instance and provides methods
    to pause and resume sync operations for the local device.
    """

    def __init__(self, api_key: str, base_url: str = "http://localhost:8384"):
        """
        Initialize the Syncthing client.

        Args:
            api_key: Syncthing REST API key
            base_url: Base URL for Syncthing API (default: http://localhost:8384)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = 5  # seconds
        self._lock = threading.Lock()
        self._device_id: Optional[str] = None
        self.logger = logging.getLogger(__name__)

        # Set up headers for all requests
        self.headers = {"X-API-Key": self.api_key}

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make a request to the Syncthing API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/rest/system/status")
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            SyncthingConnectionError: If connection fails
            SyncthingAPIError: If API returns an error
        """
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("headers", {}).update(self.headers)
        kwargs.setdefault("timeout", self.timeout)

        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout as e:
            raise SyncthingConnectionError(
                "Connection to Syncthing timed out. Is Syncthing running?"
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise SyncthingConnectionError(
                "Could not connect to Syncthing. Is Syncthing running on localhost:8384?"
            ) from e
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                raise SyncthingAPIError(
                    "Invalid API key. Check your Syncthing API key in settings."
                ) from e
            raise SyncthingAPIError(f"Syncthing API error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise SyncthingConnectionError(f"Request failed: {e}") from e

    def get_device_id(self) -> str:
        """
        Get the local device ID from Syncthing.

        Returns:
            Local device ID

        Raises:
            SyncthingConnectionError: If connection fails
            SyncthingAPIError: If API returns an error
        """
        with self._lock:
            if self._device_id is None:
                try:
                    response = self._make_request("GET", "/rest/system/status")
                    data = response.json()
                    self._device_id = data.get("myID")
                    if not self._device_id:
                        raise SyncthingAPIError("Could not retrieve device ID")
                    self.logger.debug(f"Retrieved device ID: {self._device_id}")
                except Exception as e:
                    self.logger.error(f"Failed to get device ID: {e}", exc_info=True)
                    raise
            return self._device_id

    def is_paused(self) -> bool:
        """
        Check if the local device is paused.

        Returns:
            True if device is paused, False otherwise

        Raises:
            SyncthingConnectionError: If connection fails
            SyncthingAPIError: If API returns an error
        """
        with self._lock:
            try:
                device_id = self.get_device_id()
                response = self._make_request("GET", "/rest/config")
                config = response.json()

                # Find the local device in the devices list
                for device in config.get("devices", []):
                    if device.get("deviceID") == device_id:
                        is_paused = device.get("paused", False)
                        self.logger.debug(f"Device pause state: {is_paused}")
                        return is_paused

                # If device not found in config, assume not paused
                self.logger.warning("Local device not found in config, assuming not paused")
                return False
            except Exception as e:
                self.logger.error(f"Failed to check pause state: {e}", exc_info=True)
                raise

    def pause_device(self) -> None:
        """
        Pause the local device's sync operations.

        Raises:
            SyncthingConnectionError: If connection fails
            SyncthingAPIError: If API returns an error
        """
        with self._lock:
            try:
                device_id = self.get_device_id()
                self._make_request("POST", "/rest/system/pause", json={"device": device_id})
                self.logger.info("Paused Syncthing sync for local device")
            except Exception as e:
                self.logger.error(f"Failed to pause device: {e}", exc_info=True)
                raise

    def resume_device(self) -> None:
        """
        Resume the local device's sync operations.

        Raises:
            SyncthingConnectionError: If connection fails
            SyncthingAPIError: If API returns an error
        """
        with self._lock:
            try:
                device_id = self.get_device_id()
                self._make_request("POST", "/rest/system/resume", json={"device": device_id})
                self.logger.info("Resumed Syncthing sync for local device")
            except Exception as e:
                self.logger.error(f"Failed to resume device: {e}", exc_info=True)
                raise

    def test_connection(self) -> tuple[bool, str]:
        """
        Test the connection to Syncthing API.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            response = self._make_request("GET", "/rest/system/status")
            data = response.json()
            version = data.get("version", "unknown")
            device_id = data.get("myID", "unknown")
            return (
                True,
                f"Connected successfully!\nSyncthing version: {version}\nDevice ID: {device_id[:7]}...",
            )
        except SyncthingConnectionError as e:
            return False, str(e)
        except SyncthingAPIError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def get_status_text(self) -> str:
        """
        Get a human-readable status text for display in UI.

        Returns:
            Status text like "Syncing" or "Paused"
        """
        try:
            return "Paused" if self.is_paused() else "Syncing"
        except Exception:
            return "Unknown"
