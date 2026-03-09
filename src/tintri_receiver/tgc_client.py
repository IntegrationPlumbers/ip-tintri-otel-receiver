"""REST API client for Tintri Global Center."""

import logging
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class TGCRestClient:
    """REST API client for Tintri Global Center.

    Provides methods to interact with TGC REST API for discovering inventory
    and topology information.
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
        """Initialize TGC REST client.

        Args:
            base_url: Base URL of TGC (e.g., https://tgc.example.com)
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
        """Authenticate with TGC and obtain session token."""
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

            # logger.info(f"Successfully authenticated with TGC: {self.base_url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed for TGC {self.base_url}: {e}")
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
            logger.error(f"TGC API request failed: {method} {url} - {e}")
            raise

    def get_vmstores(self) -> List[Dict[str, Any]]:
        """Get list of all VMstores managed by TGC.

        Returns:
            List of VMstore information
        """
        result = self._make_request("GET", "vmstore")

        # API may return dict with 'items' key or list directly
        if isinstance(result, dict) and "items" in result:
            return result["items"]
        elif isinstance(result, list):
            return result
        return []

    def get_datastores(self) -> List[Dict[str, Any]]:
        """Get global datastore view from TGC.

        Returns:
            List of datastore information
        """
        result = self._make_request("GET", "datastore")

        if isinstance(result, dict) and "items" in result:
            return result["items"]
        elif isinstance(result, list):
            return result
        return []

    def get_vms(self) -> List[Dict[str, Any]]:
        """Get global VM list from TGC.

        Returns:
            List of VM information
        """
        result = self._make_request("GET", "vm")

        if isinstance(result, dict) and "items" in result:
            return result["items"]
        elif isinstance(result, list):
            return result
        return []

    def get_tenants(self) -> List[Dict[str, Any]]:
        """Get tenant information from TGC.

        Returns:
            List of tenant information
        """
        return []
        # !!! TODO - Verify or remove this endpoint
        # result = self._make_request("GET", "tenant")

        # if isinstance(result, dict) and "items" in result:
        #     return result["items"]
        # elif isinstance(result, list):
        #     return result
        # return []

    def get_applications(self) -> List[Dict[str, Any]]:
        """Get application groups from TGC.

        Returns:
            List of application information
        """
        result = self._make_request("GET", "application")

        if isinstance(result, dict) and "items" in result:
            return result["items"]
        elif isinstance(result, list):
            return result
        return []

    def get_hypervisors(self) -> List[Dict[str, Any]]:
        """Get hypervisor metadata from TGC.

        Returns:
            List of hypervisor information (vCenter, clusters, hosts)
        """
        # Try common endpoint names
        return []  # Disabling, not relevant
        for endpoint in ["hypervisor", "vcenter", "vcenters"]:
            try:
                result = self._make_request("GET", endpoint)

                if isinstance(result, dict) and "items" in result:
                    return result["items"]
                elif isinstance(result, list):
                    return result
            except Exception as e:
                logger.debug(f"Endpoint {endpoint} not available: {e}")
                continue

        logger.warning("No hypervisor endpoint found in TGC API")
        return []

    def get_summary(self) -> Dict[str, Any]:
        """Get fleet summary from TGC.

        Returns:
            Fleet summary including capacity, health, system count
        """
        try:
            return self._make_request("GET", "summary")
        except Exception:
            # Try alternative endpoints
            try:
                return self._make_request("GET", "capacitySummary")
            except Exception as e:
                logger.warning(f"No summary endpoint found in TGC API: {e}")
                return {}

    def get_alerts(self, cleared: bool = False) -> List[Dict[str, Any]]:
        """Get fleet-wide alerts from TGC.

        Args:
            cleared: Include cleared alerts

        Returns:
            List of alerts
        """
        params = {}
        if not cleared:
            params["cleared"] = "false"

        result = self._make_request("GET", "alert", params=params)

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
                logger.info(f"Logged out from TGC: {self.base_url}")
            except Exception as e:
                logger.warning(f"Error during logout: {e}")

        self.session.close()
