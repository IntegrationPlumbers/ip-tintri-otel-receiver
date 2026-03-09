"""Main Tintri OpenTelemetry Receiver."""

import logging
import threading
from pprint import pprint
from typing import Any, Dict, List, Optional

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricExportResult,
    MetricsData,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource

from tintri_receiver.config import TintriReceiverConfig
from tintri_receiver.tgc_client import TGCRestClient
from tintri_receiver.tgc_inventory import TGCInventoryManager
from tintri_receiver.vmstore_client import VMstoreRestClient
from tintri_receiver.vmstore_collector import VMstoreCollector

logger = logging.getLogger(__name__)


class LoggingOTLPMetricExporter(OTLPMetricExporter):
    """OTLPMetricExporter wrapper that logs each export POST."""

    def export(self, metrics_data: MetricsData, **kwargs) -> MetricExportResult:
        total_points = 0
        metric_names = []
        # pprint(metrics_data)
        for resource_metrics in metrics_data.resource_metrics:
            for scope_metrics in resource_metrics.scope_metrics:
                for metric in scope_metrics.metrics:
                    metric_names.append(metric.name)
                    if hasattr(metric, "data") and hasattr(metric.data, "data_points"):
                        total_points += len(metric.data.data_points)

        logger.info(
            f"> OTLP POST to {self._endpoint}: "
            f"{len(metric_names)} metrics, {total_points} data points"
        )
        logger.debug(f"  Metric names: {metric_names}")

        result = super().export(metrics_data, **kwargs)

        if result == MetricExportResult.SUCCESS:
            logger.info(f"> OTLP POST successful")
        else:
            logger.warning(f"> OTLP POST failed with result: {result}")

        return result


class TintriReceiver:
    """Main Tintri OpenTelemetry Receiver.

    Orchestrates metric collection from Tintri infrastructure using a two-tier
    model: TGC for inventory/topology (slow) and VMstore for metrics (fast).
    """

    def __init__(
        self,
        config: TintriReceiverConfig,
        metric_exporter: Optional[Any] = None,
    ):
        """Initialize Tintri receiver.

        Args:
            config: Receiver configuration
            metric_exporter: Optional custom metric exporter
        """
        self.config = config
        self.config.validate()
        # print(config)
        # TGC components
        self.tgc_client: Optional[TGCRestClient] = None
        self.tgc_manager: Optional[TGCInventoryManager] = None

        # VMstore components
        self.vmstore_clients: List[VMstoreRestClient] = []
        self.vmstore_collectors: List[VMstoreCollector] = []

        # Gauge cache - create each gauge only once
        self._gauges: Dict[str, Any] = {}

        # OpenTelemetry setup
        self._setup_otel(metric_exporter)

        # Collection control
        self._stop_event = threading.Event()
        self._collection_threads: List[threading.Thread] = []

        # Initialize components
        self._initialize_components()

    def _setup_otel(self, metric_exporter: Optional[Any] = None) -> None:
        """Setup OpenTelemetry metric provider.

        Args:
            metric_exporter: Optional custom metric exporter
        """
        # Create resource with attributes
        resource_attrs = {
            "service.name": "tintri-receiver",
            **self.config.resource_attributes,
        }
        resource = Resource.create(resource_attrs)

        # Setup metric exporter
        if metric_exporter is None:
            prometheus_config = self.config.exporters.get("prometheus", {})
            endpoint = prometheus_config.get("endpoint", "localhost:9090")
            # Ensure the endpoint includes the OTLP metrics path
            if not endpoint.startswith("http"):
                endpoint = f"http://{endpoint}"
            if not endpoint.endswith("/api/v1/otlp/v1/metrics"):
                endpoint = endpoint.rstrip("/") + "/api/v1/otlp/v1/metrics"
            logger.info(f"> Creating OTLP metric exporter targeting: {endpoint}")
            metric_exporter = LoggingOTLPMetricExporter(
                endpoint=endpoint,
            )
        # Create metric reader
        reader = PeriodicExportingMetricReader(
            exporter=metric_exporter,
            export_interval_millis=10000,  # 10 seconds
        )

        # Create and set meter provider
        self.meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(self.meter_provider)

        # Get meter for this receiver
        self.meter = metrics.get_meter(__name__)

        logger.info("OpenTelemetry metric provider initialized")

    def _initialize_components(self) -> None:
        """Initialize TGC and VMstore components."""
        # Initialize TGC if configured
        if self.config.tgc:
            try:
                self.tgc_client = TGCRestClient(
                    base_url=self.config.tgc.endpoint,
                    username=self.config.tgc.username,
                    password=self.config.tgc.password,
                    api_version=self.config.tgc.api_version,
                    timeout=self.config.tgc.timeout,
                    insecure_skip_verify=self.config.tgc.insecure_skip_verify,
                )
                self.tgc_client.authenticate()

                self.tgc_manager = TGCInventoryManager(
                    tgc_client=self.tgc_client,
                    refresh_interval=self.config.tgc.collection_interval,
                )

                logger.info("TGC components initialized successfully")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize TGC: {e}. Continuing without TGC."
                )
                self.tgc_client = None
                self.tgc_manager = None

        # Initialize VMstore clients and collectors
        for vmstore_config in self.config.vmstores:
            try:
                # Create VMstore client
                vmstore_client = VMstoreRestClient(
                    base_url=vmstore_config.endpoint,
                    username=vmstore_config.username,
                    password=vmstore_config.password,
                    api_version=vmstore_config.api_version,
                    timeout=vmstore_config.timeout,
                    insecure_skip_verify=vmstore_config.insecure_skip_verify,
                )
                vmstore_client.authenticate()
                self.vmstore_clients.append(vmstore_client)

                # Create VMstore collector
                vmstore_id = vmstore_config.endpoint.split("//")[-1].split(":")[0]
                collector = VMstoreCollector(
                    vmstore_client=vmstore_client,
                    vmstore_id=vmstore_id,
                    tgc_manager=self.tgc_manager,
                    collect_system=vmstore_config.collect_system,
                    collect_datastores=vmstore_config.collect_datastores,
                    collect_vms=vmstore_config.collect_vms,
                    collect_vdisks=vmstore_config.collect_vdisks,
                    vdisk_capacity_collection=vmstore_config.vdisk_capacity_collection,
                )
                self.vmstore_collectors.append(collector)

                logger.info(f"VMstore {vmstore_id} initialized successfully")
            except Exception as e:
                logger.error(
                    f"Failed to initialize VMstore {vmstore_config.endpoint}: {e}"
                )

    def start(self) -> None:
        """Start the receiver and begin metric collection."""
        logger.info("Starting Tintri receiver...")

        # Start TGC inventory manager
        if self.tgc_manager:
            self.tgc_manager.start()

        # Start collection threads for each VMstore
        for i, collector in enumerate(self.vmstore_collectors):
            # pprint(collector)
            vmstore_config = self.config.vmstores[i]

            thread = threading.Thread(
                target=self._collection_loop,
                args=(collector, vmstore_config.collection_interval),
                daemon=True,
            )
            thread.start()
            self._collection_threads.append(thread)

        logger.info(
            f"Tintri receiver started with {len(self.vmstore_collectors)} VMstore(s)"
        )

    def stop(self) -> None:
        """Stop the receiver and cleanup resources."""
        logger.info("Stopping Tintri receiver...")

        # Signal all threads to stop
        self._stop_event.set()

        # Wait for collection threads
        for thread in self._collection_threads:
            thread.join(timeout=5)

        # Stop TGC manager
        if self.tgc_manager:
            self.tgc_manager.stop()

        # Close VMstore clients
        for client in self.vmstore_clients:
            try:
                client.close()
            except Exception as e:
                logger.warning(f"Error closing VMstore client: {e}")

        # Close TGC client
        if self.tgc_client:
            try:
                self.tgc_client.close()
            except Exception as e:
                logger.warning(f"Error closing TGC client: {e}")

        # Shutdown meter provider
        self.meter_provider.shutdown()

        logger.info("Tintri receiver stopped")

    def _collection_loop(self, collector: VMstoreCollector, interval: int) -> None:
        """Collection loop for a single VMstore.

        Args:
            collector: VMstore collector instance
            interval: Collection interval in seconds
        """

        while not self._stop_event.is_set():
            logger.info("> In collection Loop")
            try:
                # Collect metrics
                metrics = collector.collect_all_metrics()

                # Export metrics
                self._export_metrics(metrics)

            except Exception as e:
                logger.error(f"Error in collection loop: {e}")

            # Wait for next collection
            self._stop_event.wait(timeout=interval)

    def _export_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """Export collected metrics to OpenTelemetry.

        Args:
            metrics: List of metric dictionaries
        """
        # Group metrics by name for batch creation
        logger.info("> Exporting Metrics")
        metric_groups: Dict[str, List[Dict[str, Any]]] = {}

        for metric in metrics:
            name = metric["name"]
            if name not in metric_groups:
                metric_groups[name] = []
            metric_groups[name].append(metric)

        # Create OTEL metrics
        for metric_name, metric_list in metric_groups.items():
            logger.debug(f" > Exporting: {metric_name} ({len(metric_list)} series)")
            try:
                # Reuse cached gauge or create once
                if metric_name not in self._gauges:
                    self._gauges[metric_name] = self.meter.create_gauge(
                        name=metric_name,
                        unit=metric_list[0].get("unit", ""),
                        description=f"Tintri metric: {metric_name}",
                    )
                    logger.debug(f"   Created new gauge: {metric_name}")

                gauge = self._gauges[metric_name]

                # Record observations
                for metric in metric_list:
                    gauge.set(
                        amount=metric["value"],
                        attributes=metric.get("attributes", {}),
                    )
            except Exception as e:
                logger.warning(
                    f"Error exporting metric {metric_name}: {e}", exc_info=True
                )

        logger.info(
            f"> Exported {len(metrics)} metrics across {len(metric_groups)} metric names"
        )

    def collect_once(self) -> List[Dict[str, Any]]:
        """Collect metrics once from all VMstores.

        Useful for testing or one-time collection.

        Returns:
            List of all collected metrics
        """
        all_metrics = []

        for collector in self.vmstore_collectors:
            try:
                metrics = collector.collect_all_metrics()
                all_metrics.extend(metrics)
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")

        return all_metrics
