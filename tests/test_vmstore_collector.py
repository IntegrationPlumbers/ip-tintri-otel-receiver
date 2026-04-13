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
    
    def test_collect_system_metrics(self, collector, mock_vmstore_client, mock_tgc_manager):
        """Test collecting system metrics."""
        # Mock TGC inventory returning VMstore info (GET /vmstore is TGC-only)
        mock_tgc_manager.get_vmstore_info.return_value = {
            "uuid": {"uuid": "vs1"},
            "hostname": "vmstore1",
            "healthState": "HEALTHY",
            "cpuUtilization": 45.5,
            "memoryUtilization": 62.3,
        }

        # Mock datastore stats for aggregation
        collector._datastore_list_cache = [
            {"uuid": {"uuid": "ds1"}, "spaceTotalGiB": 1000, "spaceUsedGiB": 500},
        ]
        mock_vmstore_client.get_datastore_stats_realtime.return_value = {
            "latencyRead": 5.0,
            "latencyWrite": 3.0,
            "iopsRead": 1000,
            "iopsWrite": 500,
            "throughputReadMBps": 100.0,
            "throughputWriteMBps": 50.0,
        }

        metrics = collector.collect_system_metrics()

        # Should have system metrics
        assert len(metrics) > 0

        # Check for specific metrics
        metric_names = {m["name"] for m in metrics}
        assert "tintri.system.latency.read" in metric_names
        assert "tintri.system.cpu.utilization" in metric_names
    
    def test_collect_datastore_metrics_with_tgc(self, collector, mock_vmstore_client, mock_tgc_manager):
        """Test collecting datastore metrics using TGC inventory for UUIDs."""
        # TGC provides datastore IDs from cached /vmstore response
        mock_tgc_manager.get_datastore_ids_for_vmstore.return_value = ["ds1"]

        # VMstore fetches each datastore individually via /datastore/{uuid}
        mock_vmstore_client.get_datastore.return_value = {
            "uuid": {"uuid": "ds1"},
            "name": "datastore1",
            "spaceTotalGiB": 1000,
            "spaceUsedGiB": 750,
            "healthState": "HEALTHY",
        }

        # Mock datastore stats
        mock_vmstore_client.get_datastore_stats_realtime.return_value = {
            "items": [
                {
                    "sortedStats": [
                        {
                            "latencyTotalMs": 5.2,
                            "operationsReadIops": 1500,
                            "operationsWriteIops": 800,
                            "throughputReadMBps": 120.5,
                            "throughputWriteMBps": 85.3,
                        }
                    ]
                }
            ]
        }

        # Mock stats summary
        mock_vmstore_client.get_datastore_stats_summary.return_value = {}

        metrics = collector.collect_datastore_metrics()

        # Should have datastore metrics
        assert len(metrics) > 0

        # Verify TGC was consulted for datastore UUIDs
        mock_tgc_manager.get_datastore_ids_for_vmstore.assert_called_once_with("vmstore1")
        # Verify individual datastore was fetched by UUID
        mock_vmstore_client.get_datastore.assert_called_once_with("ds1")

        # Check for specific metrics
        metric_names = {m["name"] for m in metrics}
        assert "tintri.datastore.capacity.total" in metric_names
        assert "tintri.datastore.health.status" in metric_names

    def test_collect_datastore_metrics_without_tgc(self, mock_vmstore_client):
        """Test datastore collection falls back to VMstore /datastore when no TGC."""
        collector = VMstoreCollector(
            vmstore_client=mock_vmstore_client,
            vmstore_id="vmstore1",
            tgc_manager=None,
        )

        # VMstore lists datastores directly via GET /datastore
        mock_vmstore_client.get_datastore.return_value = {
            "items": [
                {
                    "uuid": {"uuid": "ds1"},
                    "name": "datastore1",
                    "spaceTotalGiB": 1000,
                    "spaceUsedGiB": 750,
                    "healthState": "HEALTHY",
                },
            ]
        }

        mock_vmstore_client.get_datastore_stats_realtime.return_value = {
            "items": [
                {
                    "sortedStats": [
                        {
                            "latencyTotalMs": 5.2,
                            "operationsReadIops": 1500,
                            "throughputReadMBps": 120.5,
                        }
                    ]
                }
            ]
        }
        mock_vmstore_client.get_datastore_stats_summary.return_value = {}

        metrics = collector.collect_datastore_metrics()

        assert len(metrics) > 0
        # VMstore /datastore was called without UUID (list mode)
        mock_vmstore_client.get_datastore.assert_any_call()
    
    def test_collect_vm_metrics(self, collector, mock_vmstore_client):
        """Test collecting VM metrics."""
        # Mock VM list
        mock_vmstore_client.get_vm.return_value = [
            {
                "uuid": {"uuid": "vm1"},
                "name": "vm-server1",
                "provisionedCapacityGiB": 100,
                "usedCapacityGiB": 60,
                "snapshotSpaceGiB": 15,
            },
        ]

        # Mock VM stats with paginated response structure
        mock_vmstore_client.get_vm_stats_realtime.return_value = {
            "items": [
                {
                    "sortedStats": [
                        {
                            "latencyTotalMs": 4.5,
                            "latencyDiskMs": 3.1,
                            "operationsReadIops": 500,
                            "operationsWriteIops": 300,
                            "throughputReadMBps": 45.2,
                            "throughputWriteMBps": 30.1,
                            "cpuPercent": 25.0,
                            "memoryUsagePercent": 50.0,
                            "performanceReserveUsed": 35.0,
                            "spaceUsedGiB": 120.5,
                        }
                    ]
                }
            ]
        }

        metrics = collector.collect_vm_metrics()

        # Should have VM metrics (perf stats + capacity)
        assert len(metrics) > 0

        # Check for specific metrics from new schema
        metric_names = {m["name"] for m in metrics}
        assert "tintri.vm.latency.total_ms" in metric_names
        assert "tintri.vm.iops.read" in metric_names
        assert "tintri.vm.throughput.read" in metric_names
        assert "tintri.vm.cpu.percent" in metric_names
        assert "tintri.vm.capacity.provisioned" in metric_names
    
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
    
    def test_collect_all_metrics(self, collector, mock_vmstore_client, mock_tgc_manager):
        """Test collecting all metrics at once."""
        # TGC returns no datastores for this vmstore
        mock_tgc_manager.get_datastore_ids_for_vmstore.return_value = []
        # Fallback VMstore /datastore also returns empty
        mock_vmstore_client.get_datastore.return_value = []
        mock_vmstore_client.get_vm.return_value = []
        mock_vmstore_client.get_virtual_disk.return_value = []

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
        # Datastore resolution should not happen when datastores disabled
        mock_vmstore_client.get_datastore.assert_not_called()
        mock_vmstore_client.get_virtual_disk.assert_not_called()
    
    def test_error_handling_partial_failure(self, collector, mock_vmstore_client, mock_tgc_manager):
        """Test that collector continues on partial failures."""
        # Make datastore resolution fail
        mock_tgc_manager.get_datastore_ids_for_vmstore.return_value = []
        mock_vmstore_client.get_datastore.side_effect = Exception("API error")

        # But others succeed
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
        # Setup datastore cache (individual datastore responses have nested uuid)
        collector._datastore_list_cache = [
            {"uuid": {"uuid": "ds1"}, "spaceTotalGiB": 1000, "spaceUsedGiB": 500},
            {"uuid": {"uuid": "ds2"}, "spaceTotalGiB": 2000, "spaceUsedGiB": 1500},
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
