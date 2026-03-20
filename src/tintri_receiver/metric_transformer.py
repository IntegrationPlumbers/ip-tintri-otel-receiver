"""Metric transformer for converting Tintri API responses to OTEL metrics."""

import logging
from typing import Any, Dict, List, Optional

from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader

logger = logging.getLogger(__name__)


# Health status encoding
HEALTH_STATUS_MAP = {
    "HEALTHY": 0,
    "OK": 0,
    "NORMAL": 0,
    "WARNING": 1,
    "DEGRADED": 1,
    "CRITICAL": 2,
    "ERROR": 2,
    "FAILED": 2,
    "UNKNOWN": 3,
}


class MetricTransformer:
    """Transforms Tintri API responses to OpenTelemetry metrics."""

    @staticmethod
    def calculate_capacity_pct(total: float, used: float) -> float:
        """Calculate capacity percentage.

        Args:
            total: Total capacity
            used: Used capacity

        Returns:
            Percentage used (0-100)
        """
        if total <= 0:
            return 0.0
        return (used / total) * 100.0

    @staticmethod
    def encode_health_status(status: str) -> int:
        """Encode health status string to numeric value.

        Args:
            status: Health status string

        Returns:
            Numeric value (0=healthy, 1=warning, 2=critical, 3=unknown)
        """
        return HEALTH_STATUS_MAP.get(status.upper(), 3)

    # Mapping of DatastoreStat API field names to (metric_name, unit).
    # Based on Tintri REST API v310 DatastoreStat schema.
    DATASTORE_STAT_FIELDS = [
        # Latency metrics (double, ms)
        ("latencyContentionMs", "tintri.datastore.latency.contention_ms", "ms"),
        ("latencyDifferenceFromMaxInSetMs", "tintri.datastore.latency.difference_from_max_in_set_ms", "ms"),
        ("latencyDiskMs", "tintri.datastore.latency.disk_ms", "ms"),
        ("latencyFlashMs", "tintri.datastore.latency.flash_ms", "ms"),
        ("latencyHostMs", "tintri.datastore.latency.host_ms", "ms"),
        ("latencyMirrorMs", "tintri.datastore.latency.mirror_ms", "ms"),
        ("latencyMirrorReadMs", "tintri.datastore.latency.mirror_read_ms", "ms"),
        ("latencyMirrorWriteMs", "tintri.datastore.latency.mirror_write_ms", "ms"),
        ("latencyMirrorWriteNetworkMs", "tintri.datastore.latency.mirror_write_network_ms", "ms"),
        ("latencyNetworkMs", "tintri.datastore.latency.network_ms", "ms"),
        ("latencyStorageMs", "tintri.datastore.latency.storage_ms", "ms"),
        ("latencyThrottleMs", "tintri.datastore.latency.throttle_ms", "ms"),
        ("latencyTotalMs", "tintri.datastore.latency.total_ms", "ms"),
        # Latency percentage (double, %)
        ("latencyIopsPercent", "tintri.datastore.latency.iops_percent", "%"),
        # Flash (double, %)
        ("flashHitPercent", "tintri.datastore.flash.hit_percent", "%"),
        # IO alignment (double, %)
        ("ioAlignedPercent", "tintri.datastore.io.aligned_percent", "%"),
        # Operations / IOPS (int/long)
        ("normalizedReadIops", "tintri.datastore.iops.normalized_read", "ops"),
        ("normalizedTotalIops", "tintri.datastore.iops.normalized_total", "ops"),
        ("normalizedWriteIops", "tintri.datastore.iops.normalized_write", "ops"),
        ("operationsInWeekMaximumIops", "tintri.datastore.iops.week_maximum", "ops"),
        ("operationsInWeekMinimumIops", "tintri.datastore.iops.week_minimum", "ops"),
        ("operationsReadIops", "tintri.datastore.iops.read", "ops"),
        ("operationsTotalIops", "tintri.datastore.iops.total", "ops"),
        ("operationsWriteIops", "tintri.datastore.iops.write", "ops"),
        # Throughput (double, MB/s)
        ("throughputCacheReadMBps", "tintri.datastore.throughput.cache_read", "MB/s"),
        ("throughputFlashMissMBps", "tintri.datastore.throughput.flash_miss", "MB/s"),
        ("throughputInWeekMaximumMBps", "tintri.datastore.throughput.week_maximum", "MB/s"),
        ("throughputInWeekMinimumMBps", "tintri.datastore.throughput.week_minimum", "MB/s"),
        ("throughputReadMBps", "tintri.datastore.throughput.read", "MB/s"),
        ("throughputTotalMBps", "tintri.datastore.throughput.total", "MB/s"),
        ("throughputWriteMBps", "tintri.datastore.throughput.write", "MB/s"),
        # Performance reserve (double)
        ("performanceReserveActual", "tintri.datastore.performance_reserve.actual", ""),
        ("performanceReserveAutoAllocated", "tintri.datastore.performance_reserve.auto_allocated", ""),
        ("performanceReserveChange", "tintri.datastore.performance_reserve.change", ""),
        ("performanceReserveChangePercent", "tintri.datastore.performance_reserve.change_percent", "%"),
        ("performanceReserveIfAutoAllocated", "tintri.datastore.performance_reserve.if_auto_allocated", ""),
        ("performanceReserveIfPinned", "tintri.datastore.performance_reserve.if_pinned", ""),
        ("performanceReservePinned", "tintri.datastore.performance_reserve.pinned", ""),
        ("performanceReserveRemaining", "tintri.datastore.performance_reserve.remaining", ""),
        ("performanceReserveUsed", "tintri.datastore.performance_reserve.used", ""),
        # Request size (double, KiB)
        ("requestSizeKiB", "tintri.datastore.request_size", "KiB"),
        # Counts (int)
        ("disksCount", "tintri.datastore.count.disks", "count"),
        ("vmsCount", "tintri.datastore.count.vms", "count"),
        ("replLinkCount", "tintri.datastore.count.repl_links", "count"),
        ("k8sClusterCount", "tintri.datastore.count.k8s_clusters", "count"),
        ("k8sContainerCount", "tintri.datastore.count.k8s_containers", "count"),
        ("k8sDeploymentCount", "tintri.datastore.count.k8s_deployments", "count"),
        ("k8sPersistentVolumeClaimCount", "tintri.datastore.count.k8s_pvcs", "count"),
        ("k8sPersistentVolumeCount", "tintri.datastore.count.k8s_pvs", "count"),
        ("k8sPodCount", "tintri.datastore.count.k8s_pods", "count"),
        # File counts (long)
        ("maxFiles", "tintri.datastore.files.max", "count"),
        ("numFiles", "tintri.datastore.files.count", "count"),
        # NTB recovery counts (long)
        ("ntbRecoveryCountA", "tintri.datastore.ntb_recovery.count_a", "count"),
        ("ntbRecoveryCountB", "tintri.datastore.ntb_recovery.count_b", "count"),
        # Boolean as int
        ("inactive", "tintri.datastore.inactive", ""),
    ]

    # Mapping of ReplicationStat API field names to (metric_name_suffix, unit).
    # Used for both replicationIncoming and replicationOutgoing nested objects
    # within DatastoreStat. The direction prefix is added at transform time.
    REPLICATION_STAT_FIELDS = [
        ("bytesRemainingIncomingMB", "bytes_remaining_incoming", "MB"),
        ("bytesRemainingMB", "bytes_remaining", "MB"),
        ("oneshotProgressPercent", "oneshot_progress", "%"),
        ("oneshotTimeRemainingSeconds", "oneshot_time_remaining", "s"),
        ("pathCount", "path_count", "count"),
        ("throughputIncomingLogicalMBps", "throughput_incoming_logical", "MB/s"),
        ("throughputIncomingPhysicalMBps", "throughput_incoming_physical", "MB/s"),
        ("throughputLogicalMBpday", "throughput_logical_per_day", "MB/day"),
        ("throughputLogicalMBps", "throughput_logical", "MB/s"),
        ("throughputPhysicalMBpday", "throughput_physical_per_day", "MB/day"),
        ("throughputPhysicalMBps", "throughput_physical", "MB/s"),
        ("timeRemainingSeconds", "time_remaining", "s"),
    ]

    # Mapping of DatastoreStat capacity/space/savings fields.
    DATASTORE_CAPACITY_FIELDS = [
        # Space (double, GiB)
        ("spaceTotalGiB", "tintri.datastore.capacity.total", "GiB"),
        ("spaceUsedGiB", "tintri.datastore.capacity.used", "GiB"),
        ("spaceProvisionedGiB", "tintri.datastore.capacity.provisioned", "GiB"),
        ("spaceRemainingPhysicalGiB", "tintri.datastore.capacity.remaining_physical", "GiB"),
        ("spaceUsedChangeGiB", "tintri.datastore.capacity.used_change", "GiB"),
        ("spaceUsedChangePhysicalGiB", "tintri.datastore.capacity.used_change_physical", "GiB"),
        ("spaceUsedDifferenceFromMaxInSetGiB", "tintri.datastore.capacity.used_diff_from_max", "GiB"),
        ("spaceUsedDifferenceFromMaxInSetPhysicalGiB", "tintri.datastore.capacity.used_diff_from_max_physical", "GiB"),
        ("spaceUsedLiveGiB", "tintri.datastore.capacity.used_live", "GiB"),
        ("spaceUsedLivePhysicalGiB", "tintri.datastore.capacity.used_live_physical", "GiB"),
        ("spaceUsedMappedGiB", "tintri.datastore.capacity.used_mapped", "GiB"),
        ("spaceUsedOtherGiB", "tintri.datastore.capacity.used_other", "GiB"),
        ("spaceUsedOtherPhysicalGiB", "tintri.datastore.capacity.used_other_physical", "GiB"),
        ("spaceUsedPhysicalGiB", "tintri.datastore.capacity.used_physical", "GiB"),
        ("spaceUsedReplicaSnapshotsTintriLogicalGiB", "tintri.datastore.capacity.used_replica_snapshots_logical", "GiB"),
        ("spaceUsedReplicaSnapshotsTintriPhysicalGiB", "tintri.datastore.capacity.used_replica_snapshots_physical", "GiB"),
        ("spaceUsedSnapshotsHypervisorGiB", "tintri.datastore.capacity.used_snapshots_hypervisor", "GiB"),
        ("spaceUsedSnapshotsHypervisorPhysicalGiB", "tintri.datastore.capacity.used_snapshots_hypervisor_physical", "GiB"),
        ("spaceUsedSnapshotsTintriGiB", "tintri.datastore.capacity.used_snapshots_tintri", "GiB"),
        ("spaceUsedSnapshotsTintriPhysicalGiB", "tintri.datastore.capacity.used_snapshots_tintri_physical", "GiB"),
        ("logicalMappedSpaceUsedWithFullSnapshotsGiB", "tintri.datastore.capacity.logical_mapped_with_snapshots", "GiB"),
        ("logicalUniqueSpaceUsedGiB", "tintri.datastore.capacity.logical_unique", "GiB"),
        ("thickSpaceUsedGiB", "tintri.datastore.capacity.thick_used", "GiB"),
        ("compressedSpaceUsedLive", "tintri.datastore.capacity.compressed_live", "GiB"),
        ("compressedSpaceUsedSnapshotOnly", "tintri.datastore.capacity.compressed_snapshot_only", "GiB"),
        ("liveLogicalFootprint", "tintri.datastore.capacity.live_logical_footprint", "GiB"),
        # Space percentages (double/int, %)
        ("spaceProvisionedPercent", "tintri.datastore.capacity.provisioned_percent", "%"),
        ("spaceUsedChangePercent", "tintri.datastore.capacity.used_change_percent", "%"),
        ("spaceUsedPhysicalChangePercent", "tintri.datastore.capacity.used_physical_change_percent", "%"),
        ("thickSpaceUsedPercent", "tintri.datastore.capacity.thick_used_percent", "%"),
        ("quotaProvisionedPercent", "tintri.datastore.quota.provisioned_percent", "%"),
        # Space remaining (int, days)
        ("spaceRemainingDays", "tintri.datastore.capacity.remaining_days", "days"),
        # Quota (long, GiB)
        ("totalQuotaSubscribedGiB", "tintri.datastore.quota.subscribed", "GiB"),
        # Compression / dedupe / savings factors (double)
        ("cloneDedupeFactor", "tintri.datastore.savings.clone_dedupe_factor", ""),
        ("compressionFactor", "tintri.datastore.savings.compression_factor", ""),
        ("dedupeFactor", "tintri.datastore.savings.dedupe_factor", ""),
        ("snapshotSavingsFactor", "tintri.datastore.savings.snapshot_factor", ""),
        ("spaceSavingsFactor", "tintri.datastore.savings.space_factor", ""),
        ("spaceSavingsFactorIncludingSnapshotSavings", "tintri.datastore.savings.space_factor_with_snapshots", ""),
        ("totalSpaceSavingsIncludingThinProvisioningFactor", "tintri.datastore.savings.total_with_thin_provisioning", ""),
    ]

    @staticmethod
    def _build_metrics_from_fields(
        data: Dict[str, Any],
        field_map: list,
        attributes: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Build metric dicts from a field mapping table.

        Args:
            data: Source data dictionary from API
            field_map: List of (api_field, metric_name, unit) tuples
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        metrics = []
        for api_field, metric_name, unit in field_map:
            if api_field in data:
                value = data[api_field]
                # Convert booleans to int (0/1)
                if isinstance(value, bool):
                    value = int(value)
                metrics.append(
                    {
                        "name": metric_name,
                        "value": value,
                        "unit": unit,
                        "attributes": attributes,
                    }
                )
        return metrics

    @staticmethod
    def transform_datastore_stats(
        stats: Dict[str, Any], attributes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Transform datastore statistics to metrics.

        Parses all performance fields from the Tintri DatastoreStat schema
        including latency, IOPS, throughput, performance reserve, and counts.

        Args:
            stats: Datastore stats from API (DatastoreStat object)
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        metrics = MetricTransformer._build_metrics_from_fields(
            stats, MetricTransformer.DATASTORE_STAT_FIELDS, attributes
        )

        # Extract replication stats from nested objects
        for direction in ("Incoming", "Outgoing"):
            repl_data = stats.get(f"replication{direction}")
            if repl_data and isinstance(repl_data, dict):
                repl_metrics = MetricTransformer.transform_replication_stats(
                    repl_data, direction.lower(), "datastore", attributes
                )
                metrics.extend(repl_metrics)

        return metrics

    @staticmethod
    def transform_replication_stats(
        repl_stats: Dict[str, Any],
        direction: str,
        entity_type: str,
        attributes: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Transform ReplicationStat to metrics.

        Args:
            repl_stats: ReplicationStat data from API
            direction: 'incoming' or 'outgoing'
            entity_type: 'datastore' or 'vm'
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        prefix = f"tintri.{entity_type}.replication.{direction}"
        field_map = [
            (api_field, f"{prefix}.{metric_suffix}", unit)
            for api_field, metric_suffix, unit in MetricTransformer.REPLICATION_STAT_FIELDS
        ]
        return MetricTransformer._build_metrics_from_fields(
            repl_stats, field_map, attributes
        )

    @staticmethod
    def transform_datastore_capacity(
        datastore: Dict[str, Any], attributes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Transform datastore capacity to metrics.

        Parses all space, savings, and quota fields from the Tintri
        DatastoreStat schema.

        Args:
            datastore: Datastore info from API (DatastoreStat object)
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        metrics = MetricTransformer._build_metrics_from_fields(
            datastore, MetricTransformer.DATASTORE_CAPACITY_FIELDS, attributes
        )

        # Calculate used percentage if both total and used are available
        if "spaceTotalGiB" in datastore and "spaceUsedGiB" in datastore:
            pct = MetricTransformer.calculate_capacity_pct(
                datastore["spaceTotalGiB"], datastore["spaceUsedGiB"]
            )
            metrics.append(
                {
                    "name": "tintri.datastore.capacity.used_percent",
                    "value": pct,
                    "unit": "%",
                    "attributes": attributes,
                }
            )

        # Health status
        if "healthState" in datastore:
            status_numeric = MetricTransformer.encode_health_status(
                datastore["healthState"]
            )
            metrics.append(
                {
                    "name": "tintri.datastore.health.status",
                    "value": status_numeric,
                    "unit": "",
                    "attributes": {
                        **attributes,
                        "health_status": datastore["healthState"],
                    },
                }
            )

        return metrics

    # Mapping of VirtualMachineStat API field names to (metric_name, unit).
    # Based on Tintri REST API v310 VirtualMachineStat schema.
    VM_STAT_FIELDS = [
        # Latency metrics (double, ms)
        ("latencyContentionMs", "tintri.vm.latency.contention_ms", "ms"),
        ("latencyDifferenceFromMaxInSetMs", "tintri.vm.latency.difference_from_max_in_set_ms", "ms"),
        ("latencyDiskMs", "tintri.vm.latency.disk_ms", "ms"),
        ("latencyFlashMs", "tintri.vm.latency.flash_ms", "ms"),
        ("latencyHostMs", "tintri.vm.latency.host_ms", "ms"),
        ("latencyMirrorMs", "tintri.vm.latency.mirror_ms", "ms"),
        ("latencyMirrorReadMs", "tintri.vm.latency.mirror_read_ms", "ms"),
        ("latencyMirrorWriteMs", "tintri.vm.latency.mirror_write_ms", "ms"),
        ("latencyMirrorWriteNetworkMs", "tintri.vm.latency.mirror_write_network_ms", "ms"),
        ("latencyNetworkMs", "tintri.vm.latency.network_ms", "ms"),
        ("latencyStorageMs", "tintri.vm.latency.storage_ms", "ms"),
        ("latencyThrottleMs", "tintri.vm.latency.throttle_ms", "ms"),
        ("latencyTotalMs", "tintri.vm.latency.total_ms", "ms"),
        # Latency/IO percentages (double, %)
        ("latencyIopsPercent", "tintri.vm.latency.iops_percent", "%"),
        ("flashHitPercent", "tintri.vm.flash.hit_percent", "%"),
        ("ioAlignedPercent", "tintri.vm.io.aligned_percent", "%"),
        # Operations / IOPS (int/long)
        ("normalizedReadIops", "tintri.vm.iops.normalized_read", "ops"),
        ("normalizedTotalIops", "tintri.vm.iops.normalized_total", "ops"),
        ("normalizedWriteIops", "tintri.vm.iops.normalized_write", "ops"),
        ("operationsReadIops", "tintri.vm.iops.read", "ops"),
        ("operationsTotalIops", "tintri.vm.iops.total", "ops"),
        ("operationsWriteIops", "tintri.vm.iops.write", "ops"),
        # Throughput (double, MB/s)
        ("throughputCacheReadMBps", "tintri.vm.throughput.cache_read", "MB/s"),
        ("throughputFlashMissMBps", "tintri.vm.throughput.flash_miss", "MB/s"),
        ("throughputReadMBps", "tintri.vm.throughput.read", "MB/s"),
        ("throughputTotalMBps", "tintri.vm.throughput.total", "MB/s"),
        ("throughputWriteMBps", "tintri.vm.throughput.write", "MB/s"),
        # CPU / Memory (double)
        ("cpuPercent", "tintri.vm.cpu.percent", "%"),
        ("cpuUsageMhz", "tintri.vm.cpu.usage_mhz", "MHz"),
        ("memoryUsageMiB", "tintri.vm.memory.usage_mib", "MiB"),
        ("memoryUsagePercent", "tintri.vm.memory.usage_percent", "%"),
        ("readyPercent", "tintri.vm.cpu.ready_percent", "%"),
        ("swapWaitPercent", "tintri.vm.cpu.swap_wait_percent", "%"),
        # Performance reserve (double)
        ("performanceReserveActual", "tintri.vm.performance_reserve.actual", ""),
        ("performanceReserveAutoAllocated", "tintri.vm.performance_reserve.auto_allocated", ""),
        ("performanceReserveChange", "tintri.vm.performance_reserve.change", ""),
        ("performanceReserveChangePercent", "tintri.vm.performance_reserve.change_percent", "%"),
        ("performanceReserveIfAutoAllocated", "tintri.vm.performance_reserve.if_auto_allocated", ""),
        ("performanceReserveIfPinned", "tintri.vm.performance_reserve.if_pinned", ""),
        ("performanceReservePinned", "tintri.vm.performance_reserve.pinned", ""),
        ("performanceReserveRemaining", "tintri.vm.performance_reserve.remaining", ""),
        ("performanceReserveUsed", "tintri.vm.performance_reserve.used", ""),
        # Space / Capacity (double, GiB)
        ("spaceProvisionedGiB", "tintri.vm.capacity.provisioned", "GiB"),
        ("spaceUsedGiB", "tintri.vm.capacity.used", "GiB"),
        ("spaceUsedChangeGiB", "tintri.vm.capacity.used_change", "GiB"),
        ("spaceUsedChangePercent", "tintri.vm.capacity.used_change_percent", "%"),
        ("spaceUsedChangePhysicalGiB", "tintri.vm.capacity.used_change_physical", "GiB"),
        ("spaceUsedDifferenceFromMaxInSetGiB", "tintri.vm.capacity.used_diff_from_max", "GiB"),
        ("spaceUsedDifferenceFromMaxInSetPhysicalGiB", "tintri.vm.capacity.used_diff_from_max_physical", "GiB"),
        ("spaceUsedLiveGiB", "tintri.vm.capacity.used_live", "GiB"),
        ("spaceUsedLivePhysicalGiB", "tintri.vm.capacity.used_live_physical", "GiB"),
        ("spaceUsedPhysicalGiB", "tintri.vm.capacity.used_physical", "GiB"),
        ("spaceUsedPhysicalChangePercent", "tintri.vm.capacity.used_physical_change_percent", "%"),
        ("spaceUsedSnapshotsHypervisorGiB", "tintri.vm.capacity.used_snapshots_hypervisor", "GiB"),
        ("spaceUsedSnapshotsHypervisorPhysicalGiB", "tintri.vm.capacity.used_snapshots_hypervisor_physical", "GiB"),
        ("spaceUsedSnapshotsTintriGiB", "tintri.vm.capacity.used_snapshots_tintri", "GiB"),
        ("spaceUsedSnapshotsTintriPhysicalGiB", "tintri.vm.capacity.used_snapshots_tintri_physical", "GiB"),
        ("compressedSpaceUsedLive", "tintri.vm.capacity.compressed_live", "GiB"),
        ("compressedSpaceUsedSnapshotOnly", "tintri.vm.capacity.compressed_snapshot_only", "GiB"),
        ("liveLogicalFootprint", "tintri.vm.capacity.live_logical_footprint", "GiB"),
        ("logicalSpaceUsedLiveUnshared", "tintri.vm.capacity.logical_live_unshared", "GiB"),
        ("logicalSpaceUsedSnapshotUnshared", "tintri.vm.capacity.logical_snapshot_unshared", "GiB"),
        ("physicalSpaceUsedLiveUnshared", "tintri.vm.capacity.physical_live_unshared", "GiB"),
        ("physicalSpaceUsedSnapshotUnshared", "tintri.vm.capacity.physical_snapshot_unshared", "GiB"),
        ("changeMBPerDay", "tintri.vm.capacity.change_mb_per_day", "MB/day"),
        # Savings factors (double)
        ("cloneDedupeFactor", "tintri.vm.savings.clone_dedupe_factor", ""),
        ("compressionFactor", "tintri.vm.savings.compression_factor", ""),
        ("snapshotSavingsFactor", "tintri.vm.savings.snapshot_factor", ""),
        ("spaceSavingsFactor", "tintri.vm.savings.space_factor", ""),
        ("spaceSavingsFactorIncludingSnapshotSavings", "tintri.vm.savings.space_factor_with_snapshots", ""),
        # Request size (double, KiB)
        ("requestSizeKiB", "tintri.vm.request_size", "KiB"),
        # Boolean as int
        ("inactive", "tintri.vm.inactive", ""),
    ]

    @staticmethod
    def transform_vm_stats(
        stats: Dict[str, Any], attributes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Transform VM statistics to metrics.

        Parses all performance fields from the Tintri VirtualMachineStat schema
        including latency, IOPS, throughput, CPU/memory, performance reserve,
        space/capacity, and savings factors.

        Args:
            stats: VM stats from API (VirtualMachineStat object)
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        return MetricTransformer._build_metrics_from_fields(
            stats, MetricTransformer.VM_STAT_FIELDS, attributes
        )

    @staticmethod
    def transform_vm_capacity(
        vm: Dict[str, Any], attributes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Transform VM capacity to metrics.

        Args:
            vm: VM info from API
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        metrics = []

        # Capacity metrics
        if "provisionedCapacityGiB" in vm:
            metrics.append(
                {
                    "name": "tintri.vm.capacity.provisioned",
                    "value": vm["provisionedCapacityGiB"],
                    "unit": "GB",
                    "attributes": attributes,
                }
            )

        if "usedCapacityGiB" in vm:
            metrics.append(
                {
                    "name": "tintri.vm.capacity.used",
                    "value": vm["usedCapacityGiB"],
                    "unit": "GB",
                    "attributes": attributes,
                }
            )

        if "snapshotSpaceGiB" in vm:
            metrics.append(
                {
                    "name": "tintri.vm.capacity.snapshot.used",
                    "value": vm["snapshotSpaceGiB"],
                    "unit": "GB",
                    "attributes": attributes,
                }
            )

        # QoS status
        qos_field = vm.get("qosStatus") or vm.get("performanceImpact")
        if qos_field:
            metrics.append(
                {
                    "name": "tintri.vm.qos.status",
                    "value": 1 if qos_field else 0,
                    "unit": "",
                    "attributes": {
                        **attributes,
                        "qos_status": str(qos_field),
                    },
                }
            )

        return metrics

    @staticmethod
    def transform_vdisk_stats(
        stats: Dict[str, Any], attributes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Transform VDISK statistics to metrics.

        Args:
            stats: VDISK stats from API
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        metrics = []

        # Latency metrics
        if "latencyRead" in stats:
            metrics.append(
                {
                    "name": "tintri.vdisk.latency.read",
                    "value": stats["latencyRead"],
                    "unit": "ms",
                    "attributes": attributes,
                }
            )

        if "latencyWrite" in stats:
            metrics.append(
                {
                    "name": "tintri.vdisk.latency.write",
                    "value": stats["latencyWrite"],
                    "unit": "ms",
                    "attributes": attributes,
                }
            )

        # IOPS metrics
        if "iopsRead" in stats:
            metrics.append(
                {
                    "name": "tintri.vdisk.iops.read",
                    "value": stats["iopsRead"],
                    "unit": "ops",
                    "attributes": attributes,
                }
            )

        if "iopsWrite" in stats:
            metrics.append(
                {
                    "name": "tintri.vdisk.iops.write",
                    "value": stats["iopsWrite"],
                    "unit": "ops",
                    "attributes": attributes,
                }
            )

        # Throughput metrics
        if "throughputReadMBps" in stats:
            metrics.append(
                {
                    "name": "tintri.vdisk.throughput.read",
                    "value": stats["throughputReadMBps"],
                    "unit": "MB/s",
                    "attributes": attributes,
                }
            )

        if "throughputWriteMBps" in stats:
            metrics.append(
                {
                    "name": "tintri.vdisk.throughput.write",
                    "value": stats["throughputWriteMBps"],
                    "unit": "MB/s",
                    "attributes": attributes,
                }
            )

        return metrics

    @staticmethod
    def transform_system_metrics(
        vmstore_info: Dict[str, Any],
        aggregated_stats: Dict[str, Any],
        attributes: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Transform system-level metrics.

        Args:
            vmstore_info: VMstore information
            aggregated_stats: Aggregated stats from all datastores
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        metrics = []

        # Performance metrics (aggregated from datastores)
        if "latencyRead" in aggregated_stats:
            metrics.append(
                {
                    "name": "tintri.system.latency.read",
                    "value": aggregated_stats["latencyRead"],
                    "unit": "ms",
                    "attributes": attributes,
                }
            )

        if "latencyWrite" in aggregated_stats:
            metrics.append(
                {
                    "name": "tintri.system.latency.write",
                    "value": aggregated_stats["latencyWrite"],
                    "unit": "ms",
                    "attributes": attributes,
                }
            )

        if "iopsRead" in aggregated_stats:
            metrics.append(
                {
                    "name": "tintri.system.iops.read",
                    "value": aggregated_stats["iopsRead"],
                    "unit": "ops",
                    "attributes": attributes,
                }
            )

        if "iopsWrite" in aggregated_stats:
            metrics.append(
                {
                    "name": "tintri.system.iops.write",
                    "value": aggregated_stats["iopsWrite"],
                    "unit": "ops",
                    "attributes": attributes,
                }
            )

        if "throughputReadMBps" in aggregated_stats:
            metrics.append(
                {
                    "name": "tintri.system.throughput.read",
                    "value": aggregated_stats["throughputReadMBps"],
                    "unit": "MB/s",
                    "attributes": attributes,
                }
            )

        if "throughputWriteMBps" in aggregated_stats:
            metrics.append(
                {
                    "name": "tintri.system.throughput.write",
                    "value": aggregated_stats["throughputWriteMBps"],
                    "unit": "MB/s",
                    "attributes": attributes,
                }
            )

        # Capacity metrics
        if "capacityTotalGiB" in aggregated_stats:
            metrics.append(
                {
                    "name": "tintri.system.capacity.total",
                    "value": aggregated_stats["capacityTotalGiB"],
                    "unit": "GB",
                    "attributes": attributes,
                }
            )

        if "capacityUsedGiB" in aggregated_stats:
            metrics.append(
                {
                    "name": "tintri.system.capacity.used",
                    "value": aggregated_stats["capacityUsedGiB"],
                    "unit": "GB",
                    "attributes": attributes,
                }
            )

        if (
            "capacityTotalGiB" in aggregated_stats
            and "capacityUsedGiB" in aggregated_stats
        ):
            pct = MetricTransformer.calculate_capacity_pct(
                aggregated_stats["capacityTotalGiB"],
                aggregated_stats["capacityUsedGiB"],
            )
            metrics.append(
                {
                    "name": "tintri.system.capacity.used.pct",
                    "value": pct,
                    "unit": "%",
                    "attributes": attributes,
                }
            )

        # Health and resource utilization
        if "healthState" in vmstore_info:
            status_numeric = MetricTransformer.encode_health_status(
                vmstore_info["healthState"]
            )
            metrics.append(
                {
                    "name": "tintri.system.health.status",
                    "value": status_numeric,
                    "unit": "",
                    "attributes": {
                        **attributes,
                        "health_status": vmstore_info["healthState"],
                    },
                }
            )

        if "cpuUtilization" in vmstore_info:
            metrics.append(
                {
                    "name": "tintri.system.cpu.utilization",
                    "value": vmstore_info["cpuUtilization"],
                    "unit": "%",
                    "attributes": attributes,
                }
            )

        if "memoryUtilization" in vmstore_info:
            metrics.append(
                {
                    "name": "tintri.system.memory.utilization",
                    "value": vmstore_info["memoryUtilization"],
                    "unit": "%",
                    "attributes": attributes,
                }
            )

        return metrics
