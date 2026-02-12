"""Unit tests for TGC inventory manager."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from tintri_receiver.tgc_inventory import TGCInventoryManager
from tintri_receiver.tgc_client import TGCRestClient


class TestTGCInventoryManager:
    """Tests for TGC inventory manager."""
    
    @pytest.fixture
    def mock_tgc_client(self):
        """Create a mock TGC client."""
        client = Mock(spec=TGCRestClient)
        client.base_url = "https://tgc.example.com"
        return client
    
    @pytest.fixture
    def manager(self, mock_tgc_client):
        """Create a TGC inventory manager for testing."""
        return TGCInventoryManager(
            tgc_client=mock_tgc_client,
            refresh_interval=60,
        )
    
    def test_initialization(self, manager, mock_tgc_client):
        """Test manager initialization."""
        assert manager.tgc_client == mock_tgc_client
        assert manager.refresh_interval == 60
        assert len(manager.vmstore_cache) == 0
        assert len(manager.datastore_cache) == 0
        assert len(manager.vm_cache) == 0
    
    def test_refresh_inventory(self, manager, mock_tgc_client):
        """Test inventory refresh."""
        # Mock TGC API responses
        mock_tgc_client.get_vmstores.return_value = [
            {"uuid": "vs1", "name": "vmstore1"},
            {"uuid": "vs2", "name": "vmstore2"},
        ]
        
        mock_tgc_client.get_datastores.return_value = [
            {"uuid": "ds1", "name": "datastore1", "vmstoreUuid": "vs1"},
            {"uuid": "ds2", "name": "datastore2", "vmstoreUuid": "vs2"},
        ]
        
        mock_tgc_client.get_vms.return_value = [
            {
                "uuid": "vm1",
                "name": "vm-server1",
                "datastoreUuid": "ds1",
                "tenantUuid": "t1",
            },
        ]
        
        mock_tgc_client.get_tenants.return_value = [
            {"uuid": "t1", "name": "engineering"},
        ]
        
        mock_tgc_client.get_applications.return_value = [
            {"uuid": "app1", "name": "web-app"},
        ]
        
        mock_tgc_client.get_hypervisors.return_value = [
            {"uuid": "hv1", "name": "vcenter.example.com"},
        ]
        
        # Refresh inventory
        manager.refresh_inventory()
        
        # Verify caches populated
        assert len(manager.vmstore_cache) == 2
        assert "vs1" in manager.vmstore_cache
        assert manager.vmstore_cache["vs1"]["name"] == "vmstore1"
        
        assert len(manager.datastore_cache) == 2
        assert "ds1" in manager.datastore_cache
        
        assert len(manager.vm_cache) == 1
        assert "vm1" in manager.vm_cache
        
        assert len(manager.tenant_cache) == 1
        assert "t1" in manager.tenant_cache
        
        assert len(manager.application_cache) == 1
        assert len(manager.hypervisor_cache) == 1
        
        assert manager.last_refresh > 0
    
    def test_get_vmstore_attributes(self, manager):
        """Test getting VMstore attributes."""
        manager.tgc_name = "tgc-main"
        manager.vmstore_cache = {
            "vs1": {"uuid": "vs1", "name": "vmstore1"},
        }
        
        attrs = manager.get_vmstore_attributes("vs1")
        
        assert attrs["tintri.tgc.name"] == "tgc-main"
        assert attrs["tintri.vmstore.name"] == "vmstore1"
        assert attrs["tintri.vmstore.uuid"] == "vs1"
    
    def test_get_vmstore_attributes_not_in_cache(self, manager):
        """Test getting VMstore attributes when not in cache."""
        manager.tgc_name = "tgc-main"
        
        attrs = manager.get_vmstore_attributes("vs-unknown")
        
        # Should still have TGC name
        assert attrs["tintri.tgc.name"] == "tgc-main"
        # But not VMstore name
        assert "tintri.vmstore.name" not in attrs
    
    def test_get_datastore_attributes(self, manager):
        """Test getting datastore attributes."""
        manager.tgc_name = "tgc-main"
        manager.datastore_cache = {
            "ds1": {
                "uuid": "ds1",
                "name": "datastore1",
                "vmstoreUuid": "vs1",
            },
        }
        manager.vmstore_cache = {
            "vs1": {"uuid": "vs1", "name": "vmstore1"},
        }
        
        attrs = manager.get_datastore_attributes("ds1")
        
        assert attrs["tintri.tgc.name"] == "tgc-main"
        assert attrs["tintri.datastore.name"] == "datastore1"
        assert attrs["tintri.datastore.uuid"] == "ds1"
        assert attrs["tintri.vmstore.name"] == "vmstore1"
    
    def test_get_vm_attributes(self, manager):
        """Test getting VM attributes."""
        manager.tgc_name = "tgc-main"
        manager.vm_cache = {
            "vm1": {
                "uuid": "vm1",
                "name": "vm-server1",
                "datastoreUuid": "ds1",
                "tenantUuid": "t1",
                "applicationUuid": "app1",
                "clusterName": "cluster1",
                "hostName": "esxi1.example.com",
            },
        }
        manager.datastore_cache = {
            "ds1": {"uuid": "ds1", "name": "datastore1"},
        }
        manager.tenant_cache = {
            "t1": {"uuid": "t1", "name": "engineering"},
        }
        manager.application_cache = {
            "app1": {"uuid": "app1", "name": "web-app"},
        }
        
        attrs = manager.get_vm_attributes("vm1")
        
        assert attrs["tintri.tgc.name"] == "tgc-main"
        assert attrs["tintri.vm.name"] == "vm-server1"
        assert attrs["tintri.vm.uuid"] == "vm1"
        assert attrs["tintri.datastore.name"] == "datastore1"
        assert attrs["tintri.tenant"] == "engineering"
        assert attrs["tintri.application"] == "web-app"
        assert attrs["tintri.hypervisor.cluster"] == "cluster1"
        assert attrs["tintri.hypervisor.host"] == "esxi1.example.com"
    
    def test_get_vm_attributes_minimal(self, manager):
        """Test getting VM attributes with minimal data."""
        manager.vm_cache = {
            "vm1": {"uuid": "vm1", "name": "vm-server1"},
        }
        
        attrs = manager.get_vm_attributes("vm1")
        
        assert attrs["tintri.vm.name"] == "vm-server1"
        assert attrs["tintri.vm.uuid"] == "vm1"
        # Should not have tenant/application if not in cache
        assert "tintri.tenant" not in attrs
        assert "tintri.application" not in attrs
    
    def test_get_vdisk_attributes(self, manager):
        """Test getting VDISK attributes."""
        manager.tgc_name = "tgc-main"
        manager.vm_cache = {
            "vm1": {"uuid": "vm1", "name": "vm-server1"},
        }
        
        attrs = manager.get_vdisk_attributes("vdisk-123", vm_uuid="vm1")
        
        assert attrs["tintri.vdisk.id"] == "vdisk-123"
        assert attrs["tintri.tgc.name"] == "tgc-main"
        assert attrs["tintri.vm.name"] == "vm-server1"
    
    def test_get_vmstore_list(self, manager):
        """Test getting VMstore list."""
        manager.vmstore_cache = {
            "vs1": {"uuid": "vs1", "name": "vmstore1"},
            "vs2": {"uuid": "vs2", "name": "vmstore2"},
        }
        
        vmstores = manager.get_vmstore_list()
        
        assert len(vmstores) == 2
        assert any(vs["uuid"] == "vs1" for vs in vmstores)
        assert any(vs["uuid"] == "vs2" for vs in vmstores)
    
    def test_start_stop(self, manager, mock_tgc_client):
        """Test starting and stopping the manager."""
        # Mock refresh to avoid actual API calls
        mock_tgc_client.get_vmstores.return_value = []
        mock_tgc_client.get_datastores.return_value = []
        mock_tgc_client.get_vms.return_value = []
        mock_tgc_client.get_tenants.return_value = []
        mock_tgc_client.get_applications.return_value = []
        mock_tgc_client.get_hypervisors.return_value = []
        
        # Start manager
        manager.start()
        assert manager._refresh_thread is not None
        assert manager._refresh_thread.is_alive()
        
        # Stop manager
        manager.stop()
        assert manager._stop_event.is_set()
    
    def test_refresh_handles_errors(self, manager, mock_tgc_client):
        """Test that refresh handles errors gracefully."""
        # Make one API call fail
        mock_tgc_client.get_vmstores.side_effect = Exception("API error")
        
        # Should raise the exception
        with pytest.raises(Exception):
            manager.refresh_inventory()
    
    def test_empty_uuid_filtered(self, manager, mock_tgc_client):
        """Test that objects without UUIDs are filtered out."""
        # Return objects with and without UUIDs
        mock_tgc_client.get_vmstores.return_value = [
            {"uuid": "vs1", "name": "vmstore1"},
            {"name": "vmstore2"},  # Missing UUID
        ]
        mock_tgc_client.get_datastores.return_value = []
        mock_tgc_client.get_vms.return_value = []
        mock_tgc_client.get_tenants.return_value = []
        mock_tgc_client.get_applications.return_value = []
        mock_tgc_client.get_hypervisors.return_value = []
        
        manager.refresh_inventory()
        
        # Only the object with UUID should be cached
        assert len(manager.vmstore_cache) == 1
        assert "vs1" in manager.vmstore_cache
