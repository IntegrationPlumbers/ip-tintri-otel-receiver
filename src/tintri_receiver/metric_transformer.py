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

    @staticmethod
    def transform_datastore_stats(
        stats: Dict[str, Any], attributes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Transform datastore statistics to metrics.

        Args:
            stats: Datastore stats from API
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        metrics = []

        # Latency metrics
        if "latencyDiskMs" in stats:
            metrics.append(
                {
                    "name": "tintri.datastore.latency.disk_ms",
                    "value": stats["latencyDiskMs"],
                    "unit": "ms",
                    "attributes": attributes,
                }
            )

        if "latencyFlashMs" in stats:
            metrics.append(
                {
                    "name": "tintri.datastore.latency.flash_ms",
                    "value": stats["latencyFlashMs"],
                    "unit": "ms",
                    "attributes": attributes,
                }
            )

        if "latencyWrite" in stats:
            metrics.append(
                {
                    "name": "tintri.datastore.latency.write",
                    "value": stats["latencyWrite"],
                    "unit": "ms",
                    "attributes": attributes,
                }
            )

        # Flash Hit percentage
        if "flashHitPercent" in stats:
            metrics.append(
                {
                    "name": "tintri.datastore.flash.hit_perc",
                    "value": stats["flashHitPercent"],
                    "unit": "perc",
                    "attributes": attributes,
                }
            )

        if "iopsWrite" in stats:
            metrics.append(
                {
                    "name": "tintri.datastore.iops.write",
                    "value": stats["iopsWrite"],
                    "unit": "ops",
                    "attributes": attributes,
                }
            )

        # Throughput metrics
        if "throughputReadMBps" in stats:
            metrics.append(
                {
                    "name": "tintri.datastore.throughput.read",
                    "value": stats["throughputReadMBps"],
                    "unit": "MB/s",
                    "attributes": attributes,
                }
            )

        if "throughputWriteMBps" in stats:
            metrics.append(
                {
                    "name": "tintri.datastore.throughput.write",
                    "value": stats["throughputWriteMBps"],
                    "unit": "MB/s",
                    "attributes": attributes,
                }
            )

        return metrics

    @staticmethod
    def transform_datastore_capacity(
        datastore: Dict[str, Any], attributes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Transform datastore capacity to metrics.

        Args:
            datastore: Datastore info from API
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        metrics = []

        # Capacity metrics
        if "spaceTotalGiB" in datastore:
            metrics.append(
                {
                    "name": "tintri.datastore.capacity.total",
                    "value": datastore["spaceTotalGiB"],
                    "unit": "GB",
                    "attributes": attributes,
                }
            )

        if "spaceUsedGiB" in datastore:
            metrics.append(
                {
                    "name": "tintri.datastore.capacity.used",
                    "value": datastore["spaceUsedGiB"],
                    "unit": "GB",
                    "attributes": attributes,
                }
            )

        # Calculate percentage if both available
        if "spaceTotalGiB" in datastore and "spaceUsedGiB" in datastore:
            pct = MetricTransformer.calculate_capacity_pct(
                datastore["spaceTotalGiB"], datastore["spaceUsedGiB"]
            )
            metrics.append(
                {
                    "name": "tintri.datastore.capacity.used.pct",
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

    @staticmethod
    def transform_vm_stats(
        stats: Dict[str, Any], attributes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Transform VM statistics to metrics.

        Args:
            stats: VM stats from API
            attributes: Metric attributes

        Returns:
            List of metric dictionaries
        """
        metrics = []

        # Latency metrics
        if "latencyRead" in stats:
            metrics.append(
                {
                    "name": "tintri.vm.latency.read",
                    "value": stats["latencyRead"],
                    "unit": "ms",
                    "attributes": attributes,
                }
            )

        if "latencyWrite" in stats:
            metrics.append(
                {
                    "name": "tintri.vm.latency.write",
                    "value": stats["latencyWrite"],
                    "unit": "ms",
                    "attributes": attributes,
                }
            )

        # IOPS metrics
        if "iopsRead" in stats:
            metrics.append(
                {
                    "name": "tintri.vm.iops.read",
                    "value": stats["iopsRead"],
                    "unit": "ops",
                    "attributes": attributes,
                }
            )

        if "iopsWrite" in stats:
            metrics.append(
                {
                    "name": "tintri.vm.iops.write",
                    "value": stats["iopsWrite"],
                    "unit": "ops",
                    "attributes": attributes,
                }
            )

        # Throughput metrics
        if "throughputReadMBps" in stats:
            metrics.append(
                {
                    "name": "tintri.vm.throughput.read",
                    "value": stats["throughputReadMBps"],
                    "unit": "MB/s",
                    "attributes": attributes,
                }
            )

        if "throughputWriteMBps" in stats:
            metrics.append(
                {
                    "name": "tintri.vm.throughput.write",
                    "value": stats["throughputWriteMBps"],
                    "unit": "MB/s",
                    "attributes": attributes,
                }
            )

        return metrics

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
