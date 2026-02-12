"""Unit tests for VMstore REST client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from tintri_receiver.vmstore_client import VMstoreRestClient


class TestVMstoreRestClient:
    """Tests for VMstore REST client."""
    
    @pytest.fixture
    def client(self):
        """Create a VMstore client for testing."""
        return VMstoreRestClient(
            base_url="https://vmstore.example.com",
            username="admin",
            password="secret123",
            api_version="v310",
            timeout=30,
        )
    
    @patch("requests.Session.post")
    def test_authenticate_success(self, mock_post, client):
        """Test successful authentication."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"X-Tintri-Session-Token": "test-token-123"}
        mock_post.return_value = mock_response
        
        client.authenticate()
        
        assert client.session_token == "test-token-123"
        assert client.token_expiry > 0
        mock_post.assert_called_once()
    
    @patch("requests.Session.post")
    def test_authenticate_failure(self, mock_post, client):
        """Test authentication failure."""
        mock_post.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        
        with pytest.raises(requests.exceptions.HTTPError):
            client.authenticate()
        
        assert client.session_token is None
    
    @patch("requests.Session.request")
    def test_make_request_success(self, mock_request, client):
        """Test successful API request."""
        client.session_token = "test-token-123"
        client.token_expiry = float("inf")  # Never expires for test
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": "test"}'
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response
        
        result = client._make_request("GET", "vmstore")
        
        assert result == {"data": "test"}
        mock_request.assert_called_once()
        
        # Check headers include session token
        call_args = mock_request.call_args
        assert call_args[1]["headers"]["X-Tintri-Session-Token"] == "test-token-123"
    
    @patch("requests.Session.request")
    def test_make_request_empty_response(self, mock_request, client):
        """Test API request with empty response."""
        client.session_token = "test-token-123"
        client.token_expiry = float("inf")
        
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b""
        mock_request.return_value = mock_response
        
        result = client._make_request("GET", "vmstore")
        
        assert result == {}
    
    @patch.object(VMstoreRestClient, "authenticate")
    @patch("requests.Session.request")
    def test_ensure_authenticated_expired_token(self, mock_request, mock_auth, client):
        """Test automatic re-authentication when token expires."""
        client.session_token = "old-token"
        client.token_expiry = 0  # Expired
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": "test"}'
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response
        
        # After authentication, set new token
        def set_new_token():
            client.session_token = "new-token"
            client.token_expiry = float("inf")
        
        mock_auth.side_effect = set_new_token
        
        result = client._make_request("GET", "vmstore")
        
        mock_auth.assert_called_once()
        assert result == {"data": "test"}
    
    @patch.object(VMstoreRestClient, "_make_request")
    def test_get_vmstore_info(self, mock_request, client):
        """Test get VMstore info."""
        mock_request.return_value = {
            "uuid": "vmstore-uuid-123",
            "name": "vmstore1",
            "healthState": "HEALTHY",
        }
        
        result = client.get_vmstore_info()
        
        assert result["uuid"] == "vmstore-uuid-123"
        mock_request.assert_called_once_with("GET", "vmstore")
    
    @patch.object(VMstoreRestClient, "_make_request")
    def test_get_datastore_list(self, mock_request, client):
        """Test get datastore list."""
        mock_request.return_value = {
            "items": [
                {"uuid": "ds1", "name": "datastore1"},
                {"uuid": "ds2", "name": "datastore2"},
            ]
        }
        
        result = client.get_datastore()
        
        assert "items" in result
        assert len(result["items"]) == 2
        mock_request.assert_called_once_with("GET", "datastore")
    
    @patch.object(VMstoreRestClient, "_make_request")
    def test_get_datastore_by_uuid(self, mock_request, client):
        """Test get specific datastore by UUID."""
        mock_request.return_value = {"uuid": "ds1", "name": "datastore1"}
        
        result = client.get_datastore(uuid="ds1")
        
        assert result["uuid"] == "ds1"
        mock_request.assert_called_once_with("GET", "datastore/ds1")
    
    @patch.object(VMstoreRestClient, "_make_request")
    def test_get_datastore_stats_realtime(self, mock_request, client):
        """Test get datastore realtime stats."""
        mock_request.return_value = {
            "latencyRead": 5.2,
            "latencyWrite": 3.1,
            "iopsRead": 1500,
            "iopsWrite": 800,
        }
        
        result = client.get_datastore_stats_realtime("ds1")
        
        assert result["latencyRead"] == 5.2
        assert result["iopsRead"] == 1500
        mock_request.assert_called_once_with("GET", "datastore/ds1/statsRealtime")
    
    @patch.object(VMstoreRestClient, "_make_request")
    def test_get_vm_stats_realtime(self, mock_request, client):
        """Test get VM realtime stats."""
        mock_request.return_value = {
            "latencyRead": 2.5,
            "latencyWrite": 1.8,
            "iopsRead": 500,
            "iopsWrite": 300,
        }
        
        result = client.get_vm_stats_realtime("vm-uuid-123")
        
        assert result["latencyRead"] == 2.5
        mock_request.assert_called_once_with("GET", "vm/vm-uuid-123/statsRealtime")
    
    @patch.object(VMstoreRestClient, "_make_request")
    def test_get_vdisk_stats_realtime(self, mock_request, client):
        """Test get VDISK realtime stats."""
        mock_request.return_value = {
            "latencyRead": 1.2,
            "latencyWrite": 0.9,
            "iopsRead": 200,
            "iopsWrite": 150,
        }
        
        result = client.get_vdisk_stats_realtime("vm-123", "vdisk-456")
        
        assert result["latencyRead"] == 1.2
        mock_request.assert_called_once_with(
            "GET", "virtualDisk/vm-123/vdisk-456/statsRealtime"
        )
    
    @patch.object(VMstoreRestClient, "_make_request")
    def test_get_alerts_system(self, mock_request, client):
        """Test get system alerts."""
        mock_request.return_value = {
            "items": [
                {"uuid": "alert1", "severity": "CRITICAL"},
                {"uuid": "alert2", "severity": "WARNING"},
            ]
        }
        
        result = client.get_alerts(
            entity_type="SYSTEM", entity_uuid="vmstore-uuid", cleared=False
        )
        
        assert len(result) == 2
        mock_request.assert_called_once()
        
        # Check params
        call_args = mock_request.call_args
        assert call_args[1]["params"]["entityType"] == "SYSTEM"
        assert call_args[1]["params"]["entityUuid"] == "vmstore-uuid"
        assert call_args[1]["params"]["cleared"] == "false"
    
    @patch.object(VMstoreRestClient, "_make_request")
    def test_get_alerts_returns_list(self, mock_request, client):
        """Test get alerts when API returns list directly."""
        mock_request.return_value = [
            {"uuid": "alert1", "severity": "CRITICAL"},
        ]
        
        result = client.get_alerts()
        
        assert len(result) == 1
        assert isinstance(result, list)
    
    @patch.object(VMstoreRestClient, "_make_request")
    def test_close(self, mock_request, client):
        """Test closing the client."""
        client.session_token = "test-token-123"
        mock_request.return_value = {}
        
        client.close()
        
        mock_request.assert_called_once_with("DELETE", "session/logout")


class TestVMstoreRestClientErrors:
    """Tests for VMstore client error handling."""
    
    @patch("requests.Session.post")
    def test_network_error(self, mock_post):
        """Test handling of network errors."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        client = VMstoreRestClient(
            base_url="https://vmstore.example.com",
            username="admin",
            password="secret123",
        )
        
        with pytest.raises(requests.exceptions.ConnectionError):
            client.authenticate()
    
    @patch("requests.Session.post")
    def test_timeout_error(self, mock_post):
        """Test handling of timeout errors."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        client = VMstoreRestClient(
            base_url="https://vmstore.example.com",
            username="admin",
            password="secret123",
        )
        
        with pytest.raises(requests.exceptions.Timeout):
            client.authenticate()
    
    @patch.object(VMstoreRestClient, "authenticate")
    @patch("requests.Session.request")
    def test_api_error_404(self, mock_request, mock_auth):
        """Test handling of 404 errors."""
        mock_auth.return_value = None
        
        client = VMstoreRestClient(
            base_url="https://vmstore.example.com",
            username="admin",
            password="secret123",
        )
        client.session_token = "test-token"
        client.token_expiry = float("inf")
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_request.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            client._make_request("GET", "invalid/endpoint")
