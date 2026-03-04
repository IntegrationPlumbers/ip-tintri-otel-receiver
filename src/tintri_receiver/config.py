"""Configuration models for Tintri OpenTelemetry Receiver."""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import yaml


@dataclass
class TGCConfig:
    """Configuration for Tintri Global Center."""
    
    endpoint: str
    username: str
    password: str
    api_version: str = "v310"
    collection_interval: int = 300  # seconds
    enable_fleet_metrics: bool = True
    timeout: int = 30  # seconds
    insecure_skip_verify: bool = False
    exporters: Optional[Dict[Dict]] = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["TGCConfig"]:
        """Create TGCConfig from dictionary."""
        if not data:
            return None
        
        # Parse collection_interval (support both int and string with 's' suffix)
        interval = data.get("collection_interval", 300)
        if isinstance(interval, str):
            interval = int(interval.rstrip("s"))
        
        # Parse timeout
        timeout = data.get("timeout", 30)
        if isinstance(timeout, str):
            timeout = int(timeout.rstrip("s"))
        
        return cls(
            endpoint=data["endpoint"],
            username=data["username"],
            password=cls._resolve_env_var(data["password"]),
            api_version=data.get("api_version", "v310"),
            collection_interval=interval,
            enable_fleet_metrics=data.get("enable_fleet_metrics", True),
            timeout=timeout,
            insecure_skip_verify=data.get("insecure_skip_verify", False),
        )
    
    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """Resolve environment variable references like ${env:VAR_NAME}."""
        pattern = r"\$\{env:([^}]+)\}"
        match = re.match(pattern, value)
        if match:
            env_var = match.group(1)
            return os.getenv(env_var, "")
        return value


@dataclass
class VMstoreConfig:
    """Configuration for a single VMstore."""
    
    endpoint: str
    username: str
    password: str
    api_version: str = "v310"
    collection_interval: int = 60  # seconds
    timeout: int = 30  # seconds
    insecure_skip_verify: bool = False
    exporters: Optional[Dict[Dict]] = False
    
    # Collection toggles
    collect_system: bool = True
    collect_datastores: bool = True
    collect_vms: bool = True
    collect_vdisks: bool = True
    
    # Advanced options
    vdisk_capacity_collection: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VMstoreConfig":
        """Create VMstoreConfig from dictionary."""
        # Parse collection_interval
        interval = data.get("collection_interval", 60)
        if isinstance(interval, str):
            interval = int(interval.rstrip("s"))
        
        # Parse timeout
        timeout = data.get("timeout", 30)
        if isinstance(timeout, str):
            timeout = int(timeout.rstrip("s"))
        
        return cls(
            endpoint=data["endpoint"],
            username=data["username"],
            password=TGCConfig._resolve_env_var(data["password"]),
            api_version=data.get("api_version", "v310"),
            collection_interval=interval,
            timeout=timeout,
            insecure_skip_verify=data.get("insecure_skip_verify", False),
            collect_system=data.get("collect_system", True),
            collect_datastores=data.get("collect_datastores", True),
            collect_vms=data.get("collect_vms", True),
            collect_vdisks=data.get("collect_vdisks", True),
            vdisk_capacity_collection=data.get("vdisk_capacity_collection", False),
        )


@dataclass
class TintriReceiverConfig:
    """Main configuration for Tintri OpenTelemetry Receiver."""
    
    tgc: Optional[TGCConfig] = None
    vmstores: List[VMstoreConfig] = field(default_factory=list)
    resource_attributes: Dict[str, str] = field(default_factory=dict)
    exporters: Optional[Dict[Dict]] = False

    @classmethod
    def from_yaml(cls, file_path: str) -> "TintriReceiverConfig":
        """Load configuration from YAML file."""
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TintriReceiverConfig":
        """Create TintriReceiverConfig from dictionary."""
        # Navigate to receivers.tintri section
        receiver_data = data.get("receivers", {}).get("tintri", {})
        
        # Parse TGC config
        tgc_config = None
        if "tgc" in receiver_data:
            tgc_config = TGCConfig.from_dict(receiver_data["tgc"])
        
        # Parse VMstore configs
        vmstore_configs = []
        for vmstore_data in receiver_data.get("vmstores", []):
            vmstore_configs.append(VMstoreConfig.from_dict(vmstore_data))
        
        # Parse resource attributes
        resource_attrs = receiver_data.get("resource_attributes", {})
        
        exporters = receiver_data.get("exporters", {} )

        return cls(
            tgc=tgc_config,
            vmstores=vmstore_configs,
            resource_attributes=resource_attrs,
            exporters=exporters,
        )
    
    def validate(self) -> None:
        """Validate configuration."""
        if not self.vmstores:
            raise ValueError("At least one VMstore must be configured")
        
        for vmstore in self.vmstores:
            if not vmstore.endpoint:
                raise ValueError("VMstore endpoint is required")
            if not vmstore.username:
                raise ValueError("VMstore username is required")
            if not vmstore.password:
                raise ValueError("VMstore password is required")
        
        if self.tgc:
            if not self.tgc.endpoint:
                raise ValueError("TGC endpoint is required if TGC is configured")
            if not self.tgc.username:
                raise ValueError("TGC username is required")
            if not self.tgc.password:
                raise ValueError("TGC password is required")
