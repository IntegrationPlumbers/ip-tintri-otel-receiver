"""Unit tests for metric transformer."""

import pytest
from tintri_receiver.metric_transformer import MetricTransformer, HEALTH_STATUS_MAP


class TestMetricTransformer:
    """Tests for metric transformer."""
    
    def test_calculate_capacity_pct(self):
        """Test capacity percentage calculation."""
        # Normal case
        assert MetricTransformer.calculate_capacity_pct(100, 50) == 50.0
        assert MetricTransformer.calculate_capacity_pct(1000, 750) == 75.0
        
        # Edge cases
        assert MetricTransformer.calculate_capacity_pct(100, 0) == 0.0
        assert MetricTransformer.calculate_capacity_pct(100, 100) == 100.0
        assert MetricTransformer.calculate_capacity_pct(0, 0) == 0.0
    
    def test_encode_health_status(self):
        """Test health status encoding."""
        # Healthy statuses
        assert MetricTransformer.encode_health_status("HEALTHY") == 0
        assert MetricTransformer.encode_health_status("OK") == 0
        assert MetricTransformer.encode_health_status("NORMAL") == 0
        
        # Warning statuses
        assert MetricTransformer.encode_health_status("WARNING") == 1
        assert MetricTransformer.encode_health_status("DEGRADED") == 1
        
        # Critical statuses
        assert MetricTransformer.encode_health_status("CRITICAL") == 2
        assert MetricTransformer.encode_health_status("ERROR") == 2
        assert MetricTransformer.encode_health_status("FAILED") == 2
        
        # Unknown status
        assert MetricTransformer.encode_health_status("UNKNOWN") == 3
        assert MetricTransformer.encode_health_status("INVALID") == 3
        
        # Case insensitive
        assert MetricTransformer.encode_health_status("healthy") == 0
        assert MetricTransformer.encode_health_status("Warning") == 1
    
    def test_transform_datastore_stats(self):
        """Test datastore stats transformation."""
        stats = {
            "latencyRead": 5.2,
            "latencyWrite": 3.1,
            "iopsRead": 1500,
            "iopsWrite": 800,
            "throughputReadMBps": 120.5,
            "throughputWriteMBps": 85.3,
        }
        attributes = {
            "tintri.datastore.uuid": "ds-123",
            "tintri.datastore.name": "datastore1",
        }
        
        metrics = MetricTransformer.transform_datastore_stats(stats, attributes)
        
        # Should have 6 metrics (2 latency, 2 IOPS, 2 throughput)
        assert len(metrics) == 6
        
        # Check metric names
        metric_names = {m["name"] for m in metrics}
        assert "tintri.datastore.latency.read" in metric_names
        assert "tintri.datastore.latency.write" in metric_names
        assert "tintri.datastore.iops.read" in metric_names
        assert "tintri.datastore.iops.write" in metric_names
        assert "tintri.datastore.throughput.read" in metric_names
        assert "tintri.datastore.throughput.write" in metric_names
        
        # Check values
        latency_read = next(m for m in metrics if m["name"] == "tintri.datastore.latency.read")
        assert latency_read["value"] == 5.2
        assert latency_read["unit"] == "ms"
        assert latency_read["attributes"] == attributes
    
    def test_transform_datastore_capacity(self):
        """Test datastore capacity transformation."""
        datastore = {
            "uuid": "ds-123",
            "spaceTotalGiB": 1000,
            "spaceUsedGiB": 750,
            "healthState": "HEALTHY",
        }
        attributes = {"tintri.datastore.uuid": "ds-123"}
        
        metrics = MetricTransformer.transform_datastore_capacity(datastore, attributes)
        
        # Should have 4 metrics (total, used, pct, health)
        assert len(metrics) == 4
        
        # Check capacity metrics
        total_metric = next(m for m in metrics if m["name"] == "tintri.datastore.capacity.total")
        assert total_metric["value"] == 1000
        assert total_metric["unit"] == "GB"
        
        used_metric = next(m for m in metrics if m["name"] == "tintri.datastore.capacity.used")
        assert used_metric["value"] == 750
        
        pct_metric = next(m for m in metrics if m["name"] == "tintri.datastore.capacity.used.pct")
        assert pct_metric["value"] == 75.0
        assert pct_metric["unit"] == "%"
        
        # Check health metric
        health_metric = next(m for m in metrics if m["name"] == "tintri.datastore.health.status")
        assert health_metric["value"] == 0  # HEALTHY
        assert health_metric["attributes"]["health_status"] == "HEALTHY"
    
    def test_transform_vm_stats(self):
        """Test VM stats transformation."""
        stats = {
            "latencyRead": 2.5,
            "latencyWrite": 1.8,
            "iopsRead": 500,
            "iopsWrite": 300,
            "throughputReadMBps": 45.2,
            "throughputWriteMBps": 30.1,
        }
        attributes = {"tintri.vm.uuid": "vm-123"}
        
        metrics = MetricTransformer.transform_vm_stats(stats, attributes)
        
        assert len(metrics) == 6
        
        # Check VM-specific metric names
        metric_names = {m["name"] for m in metrics}
        assert "tintri.vm.latency.read" in metric_names
        assert "tintri.vm.iops.write" in metric_names
        assert "tintri.vm.throughput.read" in metric_names
    
    def test_transform_vm_capacity(self):
        """Test VM capacity transformation."""
        vm = {
            "uuid": "vm-123",
            "provisionedCapacityGiB": 100,
            "usedCapacityGiB": 60,
            "snapshotSpaceGiB": 15,
            "qosStatus": "NORMAL",
        }
        attributes = {"tintri.vm.uuid": "vm-123"}
        
        metrics = MetricTransformer.transform_vm_capacity(vm, attributes)
        
        # Should have 4 metrics (provisioned, used, snapshot, qos)
        assert len(metrics) == 4
        
        # Check capacity metrics
        provisioned = next(m for m in metrics if m["name"] == "tintri.vm.capacity.provisioned")
        assert provisioned["value"] == 100
        
        snapshot = next(m for m in metrics if m["name"] == "tintri.vm.capacity.snapshot.used")
        assert snapshot["value"] == 15
        
        # Check QoS metric
        qos = next(m for m in metrics if m["name"] == "tintri.vm.qos.status")
        assert qos["value"] == 1
        assert qos["attributes"]["qos_status"] == "NORMAL"
    
    def test_transform_vdisk_stats(self):
        """Test VDISK stats transformation."""
        stats = {
            "latencyRead": 1.2,
            "latencyWrite": 0.9,
            "iopsRead": 200,
            "iopsWrite": 150,
            "throughputReadMBps": 15.5,
            "throughputWriteMBps": 12.3,
        }
        attributes = {"tintri.vdisk.id": "vdisk-456"}
        
        metrics = MetricTransformer.transform_vdisk_stats(stats, attributes)
        
        assert len(metrics) == 6
        
        # Check VDISK-specific metric names
        metric_names = {m["name"] for m in metrics}
        assert "tintri.vdisk.latency.read" in metric_names
        assert "tintri.vdisk.iops.write" in metric_names
        assert "tintri.vdisk.throughput.read" in metric_names
    
    def test_transform_system_metrics(self):
        """Test system metrics transformation."""
        vmstore_info = {
            "uuid": "vmstore-123",
            "healthState": "HEALTHY",
            "cpuUtilization": 45.5,
            "memoryUtilization": 62.3,
        }
        
        aggregated_stats = {
            "latencyRead": 3.5,
            "latencyWrite": 2.8,
            "iopsRead": 5000,
            "iopsWrite": 3000,
            "throughputReadMBps": 500.0,
            "throughputWriteMBps": 350.0,
            "capacityTotalGiB": 10000,
            "capacityUsedGiB": 7500,
        }
        
        attributes = {"tintri.vmstore.uuid": "vmstore-123"}
        
        metrics = MetricTransformer.transform_system_metrics(
            vmstore_info, aggregated_stats, attributes
        )
        
        # Should have many metrics (6 perf + 3 capacity + 3 health/util)
        assert len(metrics) >= 10
        
        # Check system-level metric names
        metric_names = {m["name"] for m in metrics}
        assert "tintri.system.latency.read" in metric_names
        assert "tintri.system.iops.write" in metric_names
        assert "tintri.system.throughput.read" in metric_names
        assert "tintri.system.capacity.total" in metric_names
        assert "tintri.system.capacity.used.pct" in metric_names
        assert "tintri.system.health.status" in metric_names
        assert "tintri.system.cpu.utilization" in metric_names
        assert "tintri.system.memory.utilization" in metric_names
        
        # Check specific values
        cpu_metric = next(m for m in metrics if m["name"] == "tintri.system.cpu.utilization")
        assert cpu_metric["value"] == 45.5
        assert cpu_metric["unit"] == "%"
        
        capacity_pct = next(m for m in metrics if m["name"] == "tintri.system.capacity.used.pct")
        assert capacity_pct["value"] == 75.0
    
    def test_transform_with_missing_fields(self):
        """Test transformation handles missing fields gracefully."""
        # Empty stats
        stats = {}
        attributes = {}
        
        metrics = MetricTransformer.transform_datastore_stats(stats, attributes)
        assert len(metrics) == 0
        
        # Partial stats
        stats = {"latencyRead": 5.0}
        metrics = MetricTransformer.transform_datastore_stats(stats, attributes)
        assert len(metrics) == 1
        assert metrics[0]["name"] == "tintri.datastore.latency.read"
    
    def test_transform_preserves_attributes(self):
        """Test that transformations preserve all attributes."""
        stats = {"latencyRead": 5.0}
        attributes = {
            "tintri.datastore.uuid": "ds-123",
            "tintri.vmstore.uuid": "vmstore-123",
            "tintri.tenant": "engineering",
            "custom.attribute": "value",
        }
        
        metrics = MetricTransformer.transform_datastore_stats(stats, attributes)
        
        assert len(metrics) == 1
        assert metrics[0]["attributes"] == attributes
        assert "custom.attribute" in metrics[0]["attributes"]
