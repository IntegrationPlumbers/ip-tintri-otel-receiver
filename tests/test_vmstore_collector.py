"""Unit tests for VMstore collector."""

import pytest
from unittest.mock import Mock, MagicMock
from tintri_receiver.vmstore_collector import VMstoreCollector
from tintri_receiver.vmstore_client import VMstoreRestClient
from tintri_receiver.tgc_inventory import TGCInventoryManager


class TestVMstoreCollector:
    """Tests for VMstore collector."""
    
    @pytest.fixture
    def mock_vmstore_client(self):
        """Create a mock VMstore client."""
        return Mock(spec=VMstoreRestClient)
    
    @pytest.fixture
    def mock_tgc_manager(self):
        """Create a mock TGC inventory manager."""
        manager = Mock(spec=TGCInventoryManager)
        manager.get_vmstore_attributes.return_value = {
            "tintri.vmstore.uuid": "vs1",
            "tintri.vmstore.name": "vmstore1",
        }
        manager.get_datastore_attributes.return_value = {
            "tintri.datastore.uuid": "ds1",
            "tintri.datastore.name": "datastore1",
        }
        manager.get_vm_attributes.return_value = {
            "tintri.vm.uuid": "vm1",
            "tintri.vm.name": "vm-server1",
        }
        manager.get_vdisk_attributes.return_value = {
            "tintri.vdisk.id": "vdisk1",
        }
        return manager
    
    @pytest.fixture
    def collector(self, mock_vmstore_client, mock_tgc_manager):
        """Create a VMstore collector for testing."""
        return VMstoreCollector(
            vmstore_client=mock_vmstore_client,
            vmstore_id="vmstore1",
            tgc_manager=mock_tgc_manager,
        )
    
    def test_initialization(self, collector, mock_vmstore_client):
        """Test collector initialization."""
        assert collector.vmstore_client == mock_vmstore_client
        assert collector.vmstore_id == "vmstore1"
        assert collector.collect_system is True
        assert collector.collect_datastores is True
        assert collector.collect_vms is True
        assert collector.collect_vdisks is True
    
    def test_collect_system_metrics(self, collector, mock_vmstore_client):
        """Test collecting system metrics."""
        # Mock VMstore info
        mock_vmstore_client.get_vmstore_info.return_value = {
            "uuid": "vs1",
            "healthState": "HEALTHY",
            "cpuUtilization": 45.5,
            "memoryUtilization": 62.3,
        }
        
        # Mock datastore stats for aggregation
        collector._datastore_list_cache = [
            {"uuid": "ds1", "spaceTotalGiB": 1000, "spaceUsedGiB": 500},
        ]
        mock_vmstore_client.get_datastore_stats_realtime.return_value = {
            "latencyRead": 5.0,
            "latencyWrite": 3.0,
            "iopsRead": 1000,
            "iopsWrite": 500,
            "throughputReadMBps": 100.0,
            "throughputWriteMBps": 50.0,
        }
        
        # Mock alerts
        mock_vmstore_client.get_alerts.return_value = [
            {"uuid": "alert1"},
            {"uuid": "alert2"},
        ]
        
        metrics = collector.collect_system_metrics()
        
        # Should have system metrics
        assert len(metrics) > 0
        
        # Check for specific metrics
        metric_names = {m["name"] for m in metrics}
        assert "tintri.system.latency.read" in metric_names
        assert "tintri.system.cpu.utilization" in metric_names
        assert "tintri.system.alerts.active" in metric_names
        
        # Check alert count
        alert_metric = next(m for m in metrics if m["name"] == "tintri.system.alerts.active")
        assert alert_metric["value"] == 2
    
    def test_collect_datastore_metrics(self, collector, mock_vmstore_client):
        """Test collecting datastore metrics."""
        # Mock datastore list
        mock_vmstore_client.get_datastore.return_value = {
            "items": [
                {
                    "uuid": "ds1",
                    "name": "datastore1",
                    "spaceTotalGiB": 1000,
                    "spaceUsedGiB": 750,
                    "healthState": "HEALTHY",
                },
            ]
        }
        
        # Mock datastore stats
        mock_vmstore_client.get_datastore_stats_realtime.return_value = {
            "latencyRead": 5.2,
            "latencyWrite": 3.1,
            "iopsRead": 1500,
            "iopsWrite": 800,
            "throughputReadMBps": 120.5,
            "throughputWriteMBps": 85.3,
        }
        
        # Mock alerts
        mock_vmstore_client.get_alerts.return_value = []
        
        metrics = collector.collect_datastore_metrics()
        
        # Should have datastore metrics
        assert len(metrics) > 0
        
        # Check for specific metrics
        metric_names = {m["name"] for m in metrics}
        assert "tintri.datastore.latency.read" in metric_names
        assert "tintri.datastore.iops.write" in metric_names
        assert "tintri.datastore.capacity.total" in metric_names
        assert "tintri.datastore.health.status" in metric_names
        assert "tintri.datastore.alerts.active" in metric_names
    
    def test_collect_vm_metrics(self, collector, mock_vmstore_client):
        """Test collecting VM metrics."""
        # Mock VM list
        mock_vmstore_client.get_vm.return_value = [
            {
                "uuid": "vm1",
                "name": "vm-server1",
                "provisionedCapacityGiB": 100,
                "usedCapacityGiB": 60,
                "snapshotSpaceGiB": 15,
            },
        ]
        
        # Mock VM stats
        mock_vmstore_client.get_vm_stats_realtime.return_value = {
            "latencyRead": 2.5,
            "latencyWrite": 1.8,
            "iopsRead": 500,
            "iopsWrite": 300,
            "throughputReadMBps": 45.2,
            "throughputWriteMBps": 30.1,
        }
        
        # Mock alerts
        mock_vmstore_client.get_alerts.return_value = [{"uuid": "alert1"}]
        
        metrics = collector.collect_vm_metrics()
        
        # Should have VM metrics
        assert len(metrics) > 0
        
        # Check for specific metrics
        metric_names = {m["name"] for m in metrics}
        assert "tintri.vm.latency.read" in metric_names
        assert "tintri.vm.capacity.provisioned" in metric_names
        assert "tintri.vm.alerts.active" in metric_names
    
    def test_collect_vdisk_metrics(self, collector, mock_vmstore_client):
        """Test collecting VDISK metrics."""
        # Mock VDISK list
        mock_vmstore_client.get_virtual_disk.return_value = [
            {
                "vmId": "vm1",
                "vdiskId": "vdisk1",
                "vmUuid": "vm-uuid-1",
            },
        ]
        
        # Mock VDISK stats
        mock_vmstore_client.get_vdisk_stats_realtime.return_value = {
            "latencyRead": 1.2,
            "latencyWrite": 0.9,
            "iopsRead": 200,
            "iopsWrite": 150,
            "throughputReadMBps": 15.5,
            "throughputWriteMBps": 12.3,
        }
        
        metrics = collector.collect_vdisk_metrics()
        
        # Should have VDISK metrics
        assert len(metrics) > 0
        
        # Check for specific metrics
        metric_names = {m["name"] for m in metrics}
        assert "tintri.vdisk.latency.read" in metric_names
        assert "tintri.vdisk.iops.write" in metric_names
        assert "tintri.vdisk.throughput.read" in metric_names
    
    def test_collect_all_metrics(self, collector, mock_vmstore_client):
        """Test collecting all metrics at once."""
        # Mock all API calls
        mock_vmstore_client.get_vmstore_info.return_value = {"uuid": "vs1"}
        mock_vmstore_client.get_datastore.return_value = []
        mock_vmstore_client.get_vm.return_value = []
        mock_vmstore_client.get_virtual_disk.return_value = []
        mock_vmstore_client.get_alerts.return_value = []
        
        collector._datastore_list_cache = []
        
        metrics = collector.collect_all_metrics()
        
        # Should return a list (may be empty if no data)
        assert isinstance(metrics, list)
    
    def test_collect_with_collection_toggles(self, mock_vmstore_client, mock_tgc_manager):
        """Test collection respects toggle flags."""
        # Create collector with some collections disabled
        collector = VMstoreCollector(
            vmstore_client=mock_vmstore_client,
            vmstore_id="vmstore1",
            tgc_manager=mock_tgc_manager,
            collect_system=False,
            collect_datastores=False,
            collect_vms=True,
            collect_vdisks=False,
        )
        
        # Mock VM API calls
        mock_vmstore_client.get_vm.return_value = []
        
        metrics = collector.collect_all_metrics()
        
        # Should only call VM-related methods
        mock_vmstore_client.get_vm.assert_called_once()
        mock_vmstore_client.get_vmstore_info.assert_not_called()
        mock_vmstore_client.get_virtual_disk.assert_not_called()
    
    def test_error_handling_partial_failure(self, collector, mock_vmstore_client):
        """Test that collector continues on partial failures."""
        # Make one collection fail
        mock_vmstore_client.get_vmstore_info.side_effect = Exception("API error")
        
        # But others succeed
        mock_vmstore_client.get_datastore.return_value = []
        mock_vmstore_client.get_vm.return_value = []
        mock_vmstore_client.get_virtual_disk.return_value = []
        
        # Should not raise, just log error
        metrics = collector.collect_all_metrics()
        
        # Should still return metrics from successful collections
        assert isinstance(metrics, list)
    
    def test_attributes_without_tgc(self, mock_vmstore_client):
        """Test attribute generation without TGC manager."""
        collector = VMstoreCollector(
            vmstore_client=mock_vmstore_client,
            vmstore_id="vmstore1.example.com",
            tgc_manager=None,  # No TGC
        )
        
        attrs = collector._get_vmstore_attributes("vs1")
        
        # Should have basic attributes
        assert "tintri.vmstore.uuid" in attrs
        assert attrs["tintri.vmstore.name"] == "vmstore1.example.com"
        
        # Should not have TGC attributes
        assert "tintri.tgc.name" not in attrs
    
    def test_aggregate_datastore_stats(self, collector, mock_vmstore_client):
        """Test aggregation of datastore stats."""
        # Setup datastore cache
        collector._datastore_list_cache = [
            {"uuid": "ds1", "spaceTotalGiB": 1000, "spaceUsedGiB": 500},
            {"uuid": "ds2", "spaceTotalGiB": 2000, "spaceUsedGiB": 1500},
        ]
        
        # Mock stats for each datastore
        def mock_stats(uuid):
            if uuid == "ds1":
                return {
                    "latencyRead": 5.0,
                    "latencyWrite": 3.0,
                    "iopsRead": 1000,
                    "iopsWrite": 500,
                    "throughputReadMBps": 100.0,
                    "throughputWriteMBps": 50.0,
                }
            else:
                return {
                    "latencyRead": 7.0,
                    "latencyWrite": 4.0,
                    "iopsRead": 2000,
                    "iopsWrite": 1000,
                    "throughputReadMBps": 200.0,
                    "throughputWriteMBps": 100.0,
                }
        
        mock_vmstore_client.get_datastore_stats_realtime.side_effect = mock_stats
        
        aggregated = collector._aggregate_datastore_stats()
        
        # Check aggregated values
        assert aggregated["iopsRead"] == 3000  # 1000 + 2000
        assert aggregated["iopsWrite"] == 1500  # 500 + 1000
        assert aggregated["throughputReadMBps"] == 300.0  # 100 + 200
        assert aggregated["latencyRead"] == 6.0  # (5 + 7) / 2
        assert aggregated["capacityTotalGiB"] == 3000  # 1000 + 2000
        assert aggregated["capacityUsedGiB"] == 2000  # 500 + 1500
