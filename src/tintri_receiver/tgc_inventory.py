"""TGC Inventory Manager for topology caching and attribute enrichment."""

import logging
import threading
import time
from typing import Dict, Optional, Any, List
from tintri_receiver.tgc_client import TGCRestClient

logger = logging.getLogger(__name__)


class TGCInventoryManager:
    """Manages TGC inventory and topology cache.
    
    Periodically refreshes inventory from TGC and provides attribute lookup
    for enriching VMstore metrics.
    """
    
    def __init__(self, tgc_client: TGCRestClient, refresh_interval: int = 300):
        """Initialize TGC inventory manager.
        
        Args:
            tgc_client: TGC REST client instance
            refresh_interval: Interval in seconds to refresh inventory
        """
        self.tgc_client = tgc_client
        self.refresh_interval = refresh_interval
        
        # Topology cache
        self.vmstore_cache: Dict[str, Dict[str, Any]] = {}
        self.datastore_cache: Dict[str, Dict[str, Any]] = {}
        self.vm_cache: Dict[str, Dict[str, Any]] = {}
        self.tenant_cache: Dict[str, Dict[str, Any]] = {}
        self.application_cache: Dict[str, Dict[str, Any]] = {}
        self.hypervisor_cache: List[Dict[str, Any]] = []
        
        # Cache metadata
        self.last_refresh: float = 0
        self.tgc_name: Optional[str] = None
        
        # Thread control
        self._stop_event = threading.Event()
        self._refresh_thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """Start background inventory refresh thread."""
        self.refresh_inventory()  # Initial refresh
        
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop, daemon=True
        )
        self._refresh_thread.start()
        logger.info("TGC inventory manager started")
    
    def stop(self) -> None:
        """Stop background inventory refresh thread."""
        self._stop_event.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=5)
        logger.info("TGC inventory manager stopped")
    
    def _refresh_loop(self) -> None:
        """Background loop to refresh inventory periodically."""
        while not self._stop_event.is_set():
            time.sleep(self.refresh_interval)
            try:
                self.refresh_inventory()
            except Exception as e:
                logger.error(f"Error refreshing TGC inventory: {e}")
    
    def refresh_inventory(self) -> None:
        """Refresh inventory from TGC."""
        logger.info("Refreshing TGC inventory...")
        
        try:
            # Fetch VMstores
            vmstores = self.tgc_client.get_vmstores()
            self.vmstore_cache = {
                vs.get("uuid").get("uuid"): vs for vs in vmstores if vs.get("uuid")
            }
            logger.debug(f"Cached {len(self.vmstore_cache)} VMstores")
            
            # Fetch datastores
            datastores = self.tgc_client.get_datastores()
            self.datastore_cache = {
                ds.get("uuid").get("uuid"): ds for ds in datastores if ds.get("uuid")
            }
            logger.debug(f"Cached {len(self.datastore_cache)} datastores")
            
            # Fetch VMs
            vms = self.tgc_client.get_vms()
            self.vm_cache = {vm.get("uuid").get("uuid"): vm for vm in vms if vm.get("uuid")}
            logger.debug(f"Cached {len(self.vm_cache)} VMs")
            
            # Fetch tenants
            tenants = self.tgc_client.get_tenants()
            self.tenant_cache = {
                t.get("uuid").get("uuid"): t for t in tenants if t.get("uuid")
            }
            logger.debug(f"Cached {len(self.tenant_cache)} tenants")
            
            # Fetch applications
            # applications = self.tgc_client.get_applications()
            # self.application_cache = {
            #     app.get("uuid").get("uuid"): app for app in applications if app.get("uuid")
            # }
            # logger.debug(f"Cached {len(self.application_cache)} applications")
            
            # Fetch hypervisors
            self.hypervisor_cache = self.tgc_client.get_hypervisors()
            logger.debug(f"Cached {len(self.hypervisor_cache)} hypervisors")
            
            # Extract TGC name from first VMstore if available
            if vmstores and not self.tgc_name:
                # TGC name might be in VMstore metadata
                self.tgc_name = self.tgc_client.base_url.split("//")[-1].split(":")[0]
            
            self.last_refresh = time.time()
            logger.info(
                f"TGC inventory refreshed successfully: "
                f"{len(self.vmstore_cache)} VMstores, "
                f"{len(self.datastore_cache)} datastores, "
                f"{len(self.vm_cache)} VMs"
            )
        except Exception as e:
            logger.error(f"Failed to refresh TGC inventory: {e}")
            raise
    
    def get_vmstore_attributes(self, vmstore_uuid: str) -> Dict[str, str]:
        """Get attributes for a VMstore.
        
        Args:
            vmstore_uuid: VMstore UUID
            
        Returns:
            Dictionary of attributes
        """
        attrs = {}
        
        if self.tgc_name:
            attrs["tintri.tgc.name"] = self.tgc_name
        
        vmstore = self.vmstore_cache.get(vmstore_uuid)
        if vmstore:
            if "name" in vmstore:
                attrs["tintri.vmstore.name"] = vmstore["name"]
            if "uuid" in vmstore:
                attrs["tintri.vmstore.uuid"] = vmstore["uuid"]
        
        return attrs
    
    def get_datastore_attributes(
        self, datastore_uuid: str, vmstore_uuid: Optional[str] = None
    ) -> Dict[str, str]:
        """Get attributes for a datastore.
        
        Args:
            datastore_uuid: Datastore UUID
            vmstore_uuid: Optional VMstore UUID for additional context
            
        Returns:
            Dictionary of attributes
        """
        attrs = {}
        
        if self.tgc_name:
            attrs["tintri.tgc.name"] = self.tgc_name
        
        datastore = self.datastore_cache.get(datastore_uuid)
        if datastore:
            if "name" in datastore:
                attrs["tintri.datastore.name"] = datastore["name"]
            if "uuid" in datastore:
                attrs["tintri.datastore.uuid"] = datastore["uuid"]
            
            # Add VMstore context if available
            ds_vmstore_uuid = datastore.get("vmstoreUuid") or vmstore_uuid
            if ds_vmstore_uuid:
                vmstore_attrs = self.get_vmstore_attributes(ds_vmstore_uuid)
                attrs.update(vmstore_attrs)
        
        return attrs
    
    def get_vm_attributes(self, vm_uuid: str) -> Dict[str, str]:
        """Get attributes for a VM.
        
        Args:
            vm_uuid: VM UUID
            
        Returns:
            Dictionary of attributes including tenant, application, hypervisor
        """
        attrs = {}
        
        if self.tgc_name:
            attrs["tintri.tgc.name"] = self.tgc_name
        
        vm = self.vm_cache.get(vm_uuid)
        if vm:
            if "name" in vm:
                attrs["tintri.vm.name"] = vm["name"]
            if "uuid" in vm:
                attrs["tintri.vm.uuid"] = vm["uuid"]
            
            # Add datastore context
            if "datastoreUuid" in vm:
                ds_attrs = self.get_datastore_attributes(vm["datastoreUuid"])
                attrs.update(ds_attrs)
            
            # Add tenant
            if "tenantUuid" in vm:
                tenant = self.tenant_cache.get(vm["tenantUuid"])
                if tenant and "name" in tenant:
                    attrs["tintri.tenant"] = tenant["name"]
            
            # Add application
            if "applicationUuid" in vm:
                app = self.application_cache.get(vm["applicationUuid"])
                if app and "name" in app:
                    attrs["tintri.application"] = app["name"]
            
            # Add hypervisor context
            if "hypervisorId" in vm or "vcenterId" in vm:
                hypervisor_id = vm.get("hypervisorId") or vm.get("vcenterId")
                for hv in self.hypervisor_cache:
                    if hv.get("uuid") == hypervisor_id:
                        if "name" in hv:
                            attrs["tintri.hypervisor.manager"] = hv["name"]
                        break
            
            if "clusterName" in vm:
                attrs["tintri.hypervisor.cluster"] = vm["clusterName"]
            if "hostName" in vm:
                attrs["tintri.hypervisor.host"] = vm["hostName"]
        
        return attrs
    
    def get_vdisk_attributes(
        self, vdisk_id: str, vm_uuid: Optional[str] = None
    ) -> Dict[str, str]:
        """Get attributes for a VDISK.
        
        Args:
            vdisk_id: VDISK ID
            vm_uuid: VM UUID that owns the VDISK
            
        Returns:
            Dictionary of attributes
        """
        attrs = {"tintri.vdisk.id": vdisk_id}
        
        if self.tgc_name:
            attrs["tintri.tgc.name"] = self.tgc_name
        
        # Add VM context if available
        if vm_uuid:
            vm_attrs = self.get_vm_attributes(vm_uuid)
            attrs.update(vm_attrs)
        
        return attrs
    
    def get_datastore_ids_for_vmstore(self, vmstore_id: str) -> List[str]:
        """Get datastore IDs for a VMstore by hostname, IP, or UUID.

        Looks up the VMstore in the TGC inventory cache and returns the
        datastoreId list from the /vmstore response.

        Args:
            vmstore_id: VMstore hostname, IP address, or UUID

        Returns:
            List of datastore ID strings (empty if not found)
        """
        # Try direct UUID lookup first
        vmstore = self.vmstore_cache.get(vmstore_id)
        if vmstore:
            return vmstore.get("datastoreId", [])

        # Search by hostname or IP
        for vs in self.vmstore_cache.values():
            if vs.get("hostname") == vmstore_id or vs.get("ipAddress") == vmstore_id:
                return vs.get("datastoreId", [])

        logger.debug(f"VMstore {vmstore_id} not found in TGC inventory")
        return []

    def get_vmstore_info(self, vmstore_id: str) -> Optional[Dict[str, Any]]:
        """Get cached VMstore object by hostname, IP, or UUID.

        Args:
            vmstore_id: VMstore hostname, IP address, or UUID

        Returns:
            VMstore dict from TGC cache, or None if not found
        """
        # Try direct UUID lookup first
        vmstore = self.vmstore_cache.get(vmstore_id)
        if vmstore:
            return vmstore

        # Search by hostname or IP
        for vs in self.vmstore_cache.values():
            if vs.get("hostname") == vmstore_id or vs.get("ipAddress") == vmstore_id:
                return vs

        return None

    def get_vmstore_list(self) -> List[Dict[str, Any]]:
        """Get list of all cached VMstores.

        Returns:
            List of VMstore information
        """
        return list(self.vmstore_cache.values())
