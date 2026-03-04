"""VMstore collector for gathering metrics from a single Tintri VMstore."""

import logging
from typing import Dict, List, Optional, Any
from tintri_receiver.vmstore_client import VMstoreRestClient
from tintri_receiver.metric_transformer import MetricTransformer
from tintri_receiver.tgc_inventory import TGCInventoryManager

logger = logging.getLogger(__name__)


class VMstoreCollector:
    """Collects metrics from a single Tintri VMstore.
    
    Gathers performance, capacity, and health metrics for system, datastores,
    VMs, and VDISKs from a VMstore instance.
    """
    
    def __init__(
        self,
        vmstore_client: VMstoreRestClient,
        vmstore_id: str = "default",
        tgc_manager: Optional[TGCInventoryManager] = None,
        collect_system: bool = True,
        collect_datastores: bool = True,
        collect_vms: bool = True,
        collect_vdisks: bool = True,
        vdisk_capacity_collection: bool = False,
    ):
        """Initialize VMstore collector.
        
        Args:
            vmstore_client: VMstore REST client
            vmstore_id: VMstore identifier (UUID or hostname)
            tgc_manager: Optional TGC inventory manager for attribute enrichment
            collect_system: Collect system-level metrics
            collect_datastores: Collect datastore metrics
            collect_vms: Collect VM metrics
            collect_vdisks: Collect VDISK metrics
            vdisk_capacity_collection: Collect VDISK capacity (slower)
        """
        self.vmstore_client = vmstore_client
        self.vmstore_id = vmstore_id
        self.tgc_manager = tgc_manager
        self.collect_system = collect_system
        self.collect_datastores = collect_datastores
        self.collect_vms = collect_vms
        self.collect_vdisks = collect_vdisks
        self.vdisk_capacity_collection = vdisk_capacity_collection
        
        # Cache for object lists
        self._datastore_list_cache: List[Dict[str, Any]] = []
        self._vm_list_cache: List[Dict[str, Any]] = []
    
    def collect_all_metrics(self) -> List[Dict[str, Any]]:
        """Collect all configured metrics from VMstore.
        
        Returns:
            List of metric dictionaries
        """
        all_metrics = []
        
        try:
            # Collect system metrics
            # if self.collect_system:
            #     system_metrics = self.collect_system_metrics()
            #     all_metrics.extend(system_metrics)
            #     logger.debug(f"Collected {len(system_metrics)} system metrics")
            
            # Collect datastore metrics
            if self.collect_datastores:
                datastore_metrics = self.collect_datastore_metrics()
                all_metrics.extend(datastore_metrics)
                logger.debug(f"Collected {len(datastore_metrics)} datastore metrics")
            
            # Collect VM metrics
            if self.collect_vms:
                vm_metrics = self.collect_vm_metrics()
                all_metrics.extend(vm_metrics)
                logger.debug(f"Collected {len(vm_metrics)} VM metrics")
            
            # Collect VDISK metrics
            if self.collect_vdisks:
                vdisk_metrics = self.collect_vdisk_metrics()
                all_metrics.extend(vdisk_metrics)
                logger.debug(f"Collected {len(vdisk_metrics)} VDISK metrics")
            
            logger.info(
                f"Collected {len(all_metrics)} total metrics from VMstore {self.vmstore_id}"
            )
        except Exception as e:
            logger.error(f"Error collecting metrics from VMstore {self.vmstore_id}: {e}")
        
        return all_metrics
    
    def collect_system_metrics(self) -> List[Dict[str, Any]]:
        """Collect system-level metrics.
        
        Returns:
            List of system metric dictionaries
        """
        metrics = []
        
        try:
            # Get VMstore info
            vmstore_info = self.vmstore_client.get_vmstore_info()
            vmstore_uuid = vmstore_info.get("uuid", self.vmstore_id)
            
            # Get base attributes
            attributes = self._get_vmstore_attributes(vmstore_uuid)
            
            # Aggregate datastore stats for system-level metrics
            aggregated_stats = self._aggregate_datastore_stats()
            
            # Transform to metrics
            system_metrics = MetricTransformer.transform_system_metrics(
                vmstore_info, aggregated_stats, attributes
            )
            metrics.extend(system_metrics)
            
            # Collect system alerts
            # !!! These only apply to TGC
            # alerts = self.vmstore_client.get_alerts(
            #     entity_type="SYSTEM", entity_uuid=vmstore_uuid, cleared=False
            # )
            # metrics.append({
            #     "name": "tintri.system.alerts.active",
            #     "value": len(alerts),
            #     "unit": "count",
            #     "attributes": attributes,
            # })
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
        
        return metrics
    
    def collect_datastore_metrics(self) -> List[Dict[str, Any]]:
        """Collect datastore metrics.
        
        Returns:
            List of datastore metric dictionaries
        """
        metrics = []
        
        try:
            # Get datastore list
            datastores_response = self.vmstore_client.get_datastore()
            
            # Handle different response formats
            if isinstance(datastores_response, dict) and "items" in datastores_response:
                datastores = datastores_response["items"]
            elif isinstance(datastores_response, list):
                datastores = datastores_response
            else:
                datastores = [datastores_response] if datastores_response else []
            
            self._datastore_list_cache = datastores
            
            for datastore in datastores:
                datastore_uuid = datastore.get("uuid").get("uuid")
                if not datastore_uuid:
                    continue
                
                try:
                    # Get attributes
                    attributes = self._get_datastore_attributes(datastore_uuid)
                    
                    # Collect performance stats
                    stats = self.vmstore_client.get_datastore_stats_realtime(
                        datastore_uuid
                    )
                    perf_metrics = MetricTransformer.transform_datastore_stats(
                        stats, attributes
                    )
                    metrics.extend(perf_metrics)
                    
                    # Collect capacity metrics
                    capacity_metrics = MetricTransformer.transform_datastore_capacity(
                        datastore, attributes
                    )
                    metrics.extend(capacity_metrics)
                    
                    # # Collect alerts
                    # alerts = self.vmstore_client.get_alerts(
                    #     entity_type="DATASTORE",
                    #     entity_uuid=datastore_uuid,
                    #     cleared=False,
                    # )
                    metrics.append({
                        "name": "tintri.datastore.alerts.active",
                        "value": len(alerts),
                        "unit": "count",
                        "attributes": attributes,
                    })
                except Exception as e:
                    logger.warning(
                        f"Error collecting metrics for datastore {datastore_uuid}: {e}"
                    )
        except Exception as e:
            logger.error(f"Error collecting datastore metrics: {e}")
        
        return metrics
    
    def collect_vm_metrics(self) -> List[Dict[str, Any]]:
        """Collect VM metrics.
        
        Returns:
            List of VM metric dictionaries
        """
        metrics = []
        
        try:
            # Get VM list
            vms_response = self.vmstore_client.get_vm()
            
            # Handle different response formats
            if isinstance(vms_response, dict) and "items" in vms_response:
                vms = vms_response["items"]
            elif isinstance(vms_response, list):
                vms = vms_response
            else:
                vms = [vms_response] if vms_response else []
            
            self._vm_list_cache = vms
            
            for vm in vms:
                vm_uuid = vm.get("uuid").get("uuid")
                if not vm_uuid:
                    continue
                
                try:
                    # Get attributes
                    attributes = self._get_vm_attributes(vm_uuid)
                    
                    # Collect performance stats
                    stats = self.vmstore_client.get_vm_stats_realtime(vm_uuid)
                    perf_metrics = MetricTransformer.transform_vm_stats(
                        stats, attributes
                    )
                    metrics.extend(perf_metrics)
                    
                    # Collect capacity metrics
                    capacity_metrics = MetricTransformer.transform_vm_capacity(
                        vm, attributes
                    )
                    metrics.extend(capacity_metrics)
                    
                    # Collect alerts
                    # alerts = self.vmstore_client.get_alerts(
                    #     entity_type="VM", entity_uuid=vm_uuid, cleared=False
                    # )
                    # metrics.append({
                    #     "name": "tintri.vm.alerts.active",
                    #     "value": len(alerts),
                    #     "unit": "count",
                    #     "attributes": attributes,
                    # })
                except Exception as e:
                    logger.warning(f"Error collecting metrics for VM {vm_uuid}: {e}")
        except Exception as e:
            logger.error(f"Error collecting VM metrics: {e}")
        
        return metrics
    
    def collect_vdisk_metrics(self) -> List[Dict[str, Any]]:
        """Collect VDISK metrics.
        
        Returns:
            List of VDISK metric dictionaries
        """
        metrics = []
        
        try:
            # Get VDISK list
            vdisks_response = self.vmstore_client.get_virtual_disk()
            
            # Handle different response formats
            if isinstance(vdisks_response, dict) and "items" in vdisks_response:
                vdisks = vdisks_response["items"]
            elif isinstance(vdisks_response, list):
                vdisks = vdisks_response
            else:
                vdisks = []
            
            for vdisk in vdisks:
                vm_id = vdisk.get("vmId")
                vdisk_id = vdisk.get("vdiskId") or vdisk.get("uuid")
                
                if not vm_id or not vdisk_id:
                    continue
                
                try:
                    # Get attributes
                    vm_uuid = vdisk.get("vmUuid")
                    attributes = self._get_vdisk_attributes(vdisk_id, vm_uuid)
                    
                    # Collect performance stats
                    stats = self.vmstore_client.get_vdisk_stats_realtime(
                        vm_id, vdisk_id
                    )
                    perf_metrics = MetricTransformer.transform_vdisk_stats(
                        stats, attributes
                    )
                    metrics.extend(perf_metrics)
                    
                    # Optionally collect capacity (nice-to-have)
                    if self.vdisk_capacity_collection:
                        if "provisionedCapacityGiB" in vdisk:
                            metrics.append({
                                "name": "tintri.vdisk.capacity.provisioned",
                                "value": vdisk["provisionedCapacityGiB"],
                                "unit": "GB",
                                "attributes": attributes,
                            })
                        
                        if "usedCapacityGiB" in vdisk:
                            metrics.append({
                                "name": "tintri.vdisk.capacity.used",
                                "value": vdisk["usedCapacityGiB"],
                                "unit": "GB",
                                "attributes": attributes,
                            })
                except Exception as e:
                    logger.warning(
                        f"Error collecting metrics for VDISK {vdisk_id}: {e}"
                    )
        except Exception as e:
            logger.error(f"Error collecting VDISK metrics: {e}")
        
        return metrics
    
    def _aggregate_datastore_stats(self) -> Dict[str, Any]:
        """Aggregate datastore stats for system-level metrics.
        
        Returns:
            Aggregated statistics
        """
        aggregated = {
            "latencyRead": 0.0,
            "latencyWrite": 0.0,
            "iopsRead": 0,
            "iopsWrite": 0,
            "throughputReadMBps": 0.0,
            "throughputWriteMBps": 0.0,
            "capacityTotalGiB": 0.0,
            "capacityUsedGiB": 0.0,
        }
        
        count = 0
        
        for datastore in self._datastore_list_cache:
            datastore_uuid = datastore.get("uuid").get("uuid")
            if not datastore_uuid:
                continue
            
            try:
                stats = self.vmstore_client.get_datastore_stats_realtime(datastore_uuid)
                
                # Sum performance metrics
                aggregated["iopsRead"] += stats.get("iopsRead", 0)
                aggregated["iopsWrite"] += stats.get("iopsWrite", 0)
                aggregated["throughputReadMBps"] += stats.get("throughputReadMBps", 0)
                aggregated["throughputWriteMBps"] += stats.get("throughputWriteMBps", 0)
                
                # Average latency
                aggregated["latencyRead"] += stats.get("latencyRead", 0)
                aggregated["latencyWrite"] += stats.get("latencyWrite", 0)
                count += 1
                
                # Sum capacity
                aggregated["capacityTotalGiB"] += datastore.get("spaceTotalGiB", 0)
                aggregated["capacityUsedGiB"] += datastore.get("spaceUsedGiB", 0)
            except Exception as e:
                logger.warning(f"Error aggregating datastore {datastore_uuid}: {e}")
        
        # Calculate average latency
        if count > 0:
            aggregated["latencyRead"] /= count
            aggregated["latencyWrite"] /= count
        
        return aggregated
    
    def _get_vmstore_attributes(self, vmstore_uuid: str) -> Dict[str, str]:
        """Get attributes for VMstore.
        
        Args:
            vmstore_uuid: VMstore UUID
            
        Returns:
            Attribute dictionary
        """
        attributes = {"tintri.vmstore.uuid": vmstore_uuid}
        
        if self.tgc_manager:
            tgc_attrs = self.tgc_manager.get_vmstore_attributes(vmstore_uuid)
            attributes.update(tgc_attrs)
        else:
            # Use VMstore endpoint as name if TGC not available
            attributes["tintri.vmstore.name"] = self.vmstore_id
        
        return attributes
    
    def _get_datastore_attributes(self, datastore_uuid: str) -> Dict[str, str]:
        """Get attributes for datastore.
        
        Args:
            datastore_uuid: Datastore UUID
            
        Returns:
            Attribute dictionary
        """
        attributes = {"tintri.datastore.uuid": datastore_uuid}
        
        if self.tgc_manager:
            tgc_attrs = self.tgc_manager.get_datastore_attributes(datastore_uuid)
            attributes.update(tgc_attrs)
        
        return attributes
    
    def _get_vm_attributes(self, vm_uuid: str) -> Dict[str, str]:
        """Get attributes for VM.
        
        Args:
            vm_uuid: VM UUID
            
        Returns:
            Attribute dictionary
        """
        attributes = {"tintri.vm.uuid": vm_uuid}
        
        if self.tgc_manager:
            tgc_attrs = self.tgc_manager.get_vm_attributes(vm_uuid)
            attributes.update(tgc_attrs)
        
        return attributes
    
    def _get_vdisk_attributes(
        self, vdisk_id: str, vm_uuid: Optional[str] = None
    ) -> Dict[str, str]:
        """Get attributes for VDISK.
        
        Args:
            vdisk_id: VDISK ID
            vm_uuid: Optional VM UUID
            
        Returns:
            Attribute dictionary
        """
        attributes = {"tintri.vdisk.id": vdisk_id}
        
        if self.tgc_manager:
            tgc_attrs = self.tgc_manager.get_vdisk_attributes(vdisk_id, vm_uuid)
            attributes.update(tgc_attrs)
        
        return attributes
