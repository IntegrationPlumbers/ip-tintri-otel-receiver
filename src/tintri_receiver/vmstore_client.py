"""REST API client for Tintri VMstore."""

import logging
import time
from pprint import pprint
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class VMstoreRestClient:
    """REST API client for Tintri VMstore.

    Provides methods to interact with VMstore REST API v3.10 for collecting
    performance, capacity, and health metrics.
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        api_version: str = "v310",
        full_api_version: str = "v310.191",
        timeout: int = 30,
        insecure_skip_verify: bool = False,
    ):
        """Initialize VMstore REST client.

        Args:
            base_url: Base URL of VMstore (e.g., https://vmstore1.example.com)
            username: API username
            password: API password
            api_version: API version (default: v310)
            timeout: Request timeout in seconds
            insecure_skip_verify: Skip SSL certificate verification
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.api_version = api_version
        self.full_api_version = full_api_version
        self.timeout = timeout
        self.session_token: Optional[str] = None
        self.token_expiry: float = 0

        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        if insecure_skip_verify:
            self.session.verify = False
            requests.packages.urllib3.disable_warnings()

    def authenticate(self) -> None:
        """Authenticate with VMstore and obtain session token."""
        url = f"{self.base_url}/api/{self.api_version}/session/login"

        try:
            response = self.session.post(
                url,
                json={
                    "typeId": "com.tintri.api.rest.vcommon.dto.rbac.RestApiCredentials",
                    "username": self.username,
                    "password": self.password,
                    "fullApiVersion": self.full_api_version,
                    "authType": "LOCAL",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()

            self.session_token = response.headers.get("X-Tintri-Session-Token")
            # Token typically valid for 30 minutes, refresh after 25 minutes
            self.token_expiry = time.time() + (25 * 60)

            # logger.info(f"Successfully authenticated with VMstore: {self.base_url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed for {self.base_url}: {e}")
            raise

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid session token."""
        if not self.session_token or time.time() >= self.token_expiry:
            self.authenticate()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make authenticated API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL and version)
            params: Query parameters
            json_data: JSON request body

        Returns:
            Response JSON data
        """
        self._ensure_authenticated()

        url = f"{self.base_url}/api/{self.api_version}/{endpoint.lstrip('/')}"
        headers = {"X-Tintri-Session-Token": self.session_token}

        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=self.timeout,
            )

            response.raise_for_status()

            # Handle empty responses
            if response.status_code == 204 or not response.content:
                return {}

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            raise

    def get_vmstore_info(self) -> Dict[str, Any]:
        """Get VMstore system information.

        Returns:
            VMstore information including health, capacity, CPU, memory
        """
        return self._make_request("GET", "vmstore")

    def get_datastore(self, uuid: Optional[str] = None) -> Any:
        """Get datastore information.

        Args:
            uuid: Datastore UUID (if None, returns list of all datastores)

        Returns:
            Datastore info or list of datastores
        """
        if uuid:
            return self._make_request("GET", f"datastore/{uuid}")
        return self._make_request("GET", "datastore")

    def get_datastore_stats_realtime(self, uuid: str) -> Dict[str, Any]:
        """Get real-time statistics for a datastore.

        Args:
            uuid: Datastore UUID

        Returns:
            Real-time stats including latency, IOPS, throughput
        """
        return self._make_request("GET", f"datastore/{uuid}/statsRealtime")

    def get_vm(self, uuid: Optional[str] = None) -> Any:
        """Get VM information.

        Args:
            uuid: VM UUID (if None, returns list of all VMs)

        Returns:
            VM info or list of VMs
        """
        if uuid:
            return self._make_request("GET", f"vm/{uuid}")
        return self._make_request("GET", "vm")

    def get_vm_stats_realtime(self, uuid: str) -> Dict[str, Any]:
        """Get real-time statistics for a VM.

        Args:
            uuid: VM UUID

        Returns:
            Real-time stats including latency, IOPS, throughput
        """
        return self._make_request("GET", f"vm/{uuid}/statsRealtime")

    def get_virtual_disk(
        self, vm_id: Optional[str] = None, vdisk_id: Optional[str] = None
    ) -> Any:
        """Get virtual disk information.

        Args:
            vm_id: VM ID
            vdisk_id: VDISK ID

        Returns:
            VDISK info or list of VDISKs
        """
        if vm_id and vdisk_id:
            return self._make_request("GET", f"virtualDisk/{vm_id}/{vdisk_id}")
        return self._make_request("GET", "virtualDisk")

    def get_vdisk_stats_realtime(self, vm_id: str, vdisk_id: str) -> Dict[str, Any]:
        """Get real-time statistics for a virtual disk.

        Args:
            vm_id: VM ID
            vdisk_id: VDISK ID

        Returns:
            Real-time stats including latency, IOPS, throughput
        """
        return self._make_request(
            "GET", f"virtualDisk/{vm_id}/{vdisk_id}/statsRealtime"
        )

    def get_alerts(
        self,
        entity_type: Optional[str] = None,
        entity_uuid: Optional[str] = None,
        cleared: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get alerts.

        Args:
            entity_type: Filter by entity type (SYSTEM, DATASTORE, VM, VIRTUAL_DISK)
            entity_uuid: Filter by entity UUID
            cleared: Include cleared alerts

        Returns:
            List of alerts
        """
        params = {}
        if entity_type:
            params["entityType"] = entity_type
        if entity_uuid:
            params["entityUuid"] = entity_uuid
        if not cleared:
            params["cleared"] = "false"

        result = self._make_request("GET", "alert/filter", params=params)

        # API may return dict with 'items' key or list directly
        if isinstance(result, dict) and "items" in result:
            return result["items"]
        elif isinstance(result, list):
            return result
        return []

    def close(self) -> None:
        """Close the session and logout."""
        if self.session_token:
            try:
                self._make_request("DELETE", "session/logout")
                # logger.info(f"Logged out from VMstore: {self.base_url}")
            except Exception as e:
                logger.warning(f"Error during logout: {e}")

        self.session.close()
