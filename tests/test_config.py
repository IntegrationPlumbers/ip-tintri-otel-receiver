"""Unit tests for configuration module."""

import os
import pytest
import tempfile
from tintri_receiver.config import (
    TintriReceiverConfig,
    TGCConfig,
    VMstoreConfig,
)


class TestTGCConfig:
    """Tests for TGC configuration."""
    
    def test_from_dict_basic(self):
        """Test basic TGC config creation from dict."""
        data = {
            "endpoint": "https://tgc.example.com",
            "username": "admin",
            "password": "secret123",
        }
        
        config = TGCConfig.from_dict(data)
        
        assert config.endpoint == "https://tgc.example.com"
        assert config.username == "admin"
        assert config.password == "secret123"
        assert config.api_version == "v310"
        assert config.collection_interval == 300
    
    def test_from_dict_with_all_options(self):
        """Test TGC config with all options."""
        data = {
            "endpoint": "https://tgc.example.com",
            "username": "admin",
            "password": "secret123",
            "api_version": "v400",
            "collection_interval": "600s",
            "enable_fleet_metrics": False,
            "timeout": "60s",
            "insecure_skip_verify": True,
        }
        
        config = TGCConfig.from_dict(data)
        
        assert config.api_version == "v400"
        assert config.collection_interval == 600
        assert config.enable_fleet_metrics is False
        assert config.timeout == 60
        assert config.insecure_skip_verify is True
    
    def test_env_var_resolution(self):
        """Test environment variable resolution in password."""
        os.environ["TEST_TGC_PASSWORD"] = "env_password"
        
        data = {
            "endpoint": "https://tgc.example.com",
            "username": "admin",
            "password": "${env:TEST_TGC_PASSWORD}",
        }
        
        config = TGCConfig.from_dict(data)
        
        assert config.password == "env_password"
        
        # Cleanup
        del os.environ["TEST_TGC_PASSWORD"]
    
    def test_none_data(self):
        """Test from_dict with None data."""
        config = TGCConfig.from_dict(None)
        assert config is None


class TestVMstoreConfig:
    """Tests for VMstore configuration."""
    
    def test_from_dict_basic(self):
        """Test basic VMstore config creation."""
        data = {
            "endpoint": "https://vmstore1.example.com",
            "username": "admin",
            "password": "secret123",
        }
        
        config = VMstoreConfig.from_dict(data)
        
        assert config.endpoint == "https://vmstore1.example.com"
        assert config.username == "admin"
        assert config.password == "secret123"
        assert config.collection_interval == 60
        assert config.collect_system is True
        assert config.collect_vdisks is True
    
    def test_from_dict_with_collection_toggles(self):
        """Test VMstore config with collection toggles."""
        data = {
            "endpoint": "https://vmstore1.example.com",
            "username": "admin",
            "password": "secret123",
            "collect_system": False,
            "collect_datastores": False,
            "collect_vms": True,
            "collect_vdisks": False,
            "vdisk_capacity_collection": True,
        }
        
        config = VMstoreConfig.from_dict(data)
        
        assert config.collect_system is False
        assert config.collect_datastores is False
        assert config.collect_vms is True
        assert config.collect_vdisks is False
        assert config.vdisk_capacity_collection is True


class TestTintriReceiverConfig:
    """Tests for main receiver configuration."""
    
    def test_from_dict_minimal(self):
        """Test minimal configuration."""
        data = {
            "receivers": {
                "tintri": {
                    "vmstores": [
                        {
                            "endpoint": "https://vmstore1.example.com",
                            "username": "admin",
                            "password": "secret123",
                        }
                    ]
                }
            }
        }
        
        config = TintriReceiverConfig.from_dict(data)
        
        assert config.tgc is None
        assert len(config.vmstores) == 1
        assert config.vmstores[0].endpoint == "https://vmstore1.example.com"
    
    def test_from_dict_with_tgc(self):
        """Test configuration with TGC."""
        data = {
            "receivers": {
                "tintri": {
                    "tgc": {
                        "endpoint": "https://tgc.example.com",
                        "username": "tgc_admin",
                        "password": "tgc_password",
                    },
                    "vmstores": [
                        {
                            "endpoint": "https://vmstore1.example.com",
                            "username": "admin",
                            "password": "secret123",
                        }
                    ],
                }
            }
        }
        
        config = TintriReceiverConfig.from_dict(data)
        
        assert config.tgc is not None
        assert config.tgc.endpoint == "https://tgc.example.com"
        assert config.tgc.username == "tgc_admin"
        assert len(config.vmstores) == 1
    
    def test_from_dict_with_multiple_vmstores(self):
        """Test configuration with multiple VMstores."""
        data = {
            "receivers": {
                "tintri": {
                    "vmstores": [
                        {
                            "endpoint": "https://vmstore1.example.com",
                            "username": "admin1",
                            "password": "secret1",
                        },
                        {
                            "endpoint": "https://vmstore2.example.com",
                            "username": "admin2",
                            "password": "secret2",
                        },
                    ]
                }
            }
        }
        
        config = TintriReceiverConfig.from_dict(data)
        
        assert len(config.vmstores) == 2
        assert config.vmstores[0].endpoint == "https://vmstore1.example.com"
        assert config.vmstores[1].endpoint == "https://vmstore2.example.com"
    
    def test_from_dict_with_resource_attributes(self):
        """Test configuration with resource attributes."""
        data = {
            "receivers": {
                "tintri": {
                    "vmstores": [
                        {
                            "endpoint": "https://vmstore1.example.com",
                            "username": "admin",
                            "password": "secret123",
                        }
                    ],
                    "resource_attributes": {
                        "tintri.site": "datacenter-east",
                        "tintri.environment": "production",
                    },
                }
            }
        }
        
        config = TintriReceiverConfig.from_dict(data)
        
        assert config.resource_attributes["tintri.site"] == "datacenter-east"
        assert config.resource_attributes["tintri.environment"] == "production"
    
    def test_from_yaml(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
receivers:
  tintri:
    tgc:
      endpoint: https://tgc.example.com
      username: admin
      password: secret123
    vmstores:
      - endpoint: https://vmstore1.example.com
        username: admin
        password: secret456
    resource_attributes:
      tintri.site: datacenter-west
"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            config = TintriReceiverConfig.from_yaml(temp_path)
            
            assert config.tgc is not None
            assert config.tgc.endpoint == "https://tgc.example.com"
            assert len(config.vmstores) == 1
            assert config.resource_attributes["tintri.site"] == "datacenter-west"
        finally:
            os.unlink(temp_path)
    
    def test_validate_success(self):
        """Test successful validation."""
        config = TintriReceiverConfig(
            vmstores=[
                VMstoreConfig(
                    endpoint="https://vmstore1.example.com",
                    username="admin",
                    password="secret123",
                )
            ]
        )
        
        # Should not raise
        config.validate()
    
    def test_validate_no_vmstores(self):
        """Test validation fails with no VMstores."""
        config = TintriReceiverConfig(vmstores=[])
        
        with pytest.raises(ValueError, match="At least one VMstore"):
            config.validate()
    
    def test_validate_missing_vmstore_endpoint(self):
        """Test validation fails with missing VMstore endpoint."""
        config = TintriReceiverConfig(
            vmstores=[
                VMstoreConfig(
                    endpoint="",
                    username="admin",
                    password="secret123",
                )
            ]
        )
        
        with pytest.raises(ValueError, match="endpoint is required"):
            config.validate()
    
    def test_validate_missing_vmstore_credentials(self):
        """Test validation fails with missing credentials."""
        config = TintriReceiverConfig(
            vmstores=[
                VMstoreConfig(
                    endpoint="https://vmstore1.example.com",
                    username="",
                    password="secret123",
                )
            ]
        )
        
        with pytest.raises(ValueError, match="username is required"):
            config.validate()
    
    def test_validate_tgc_missing_endpoint(self):
        """Test validation fails with TGC missing endpoint."""
        config = TintriReceiverConfig(
            tgc=TGCConfig(
                endpoint="",
                username="admin",
                password="secret123",
            ),
            vmstores=[
                VMstoreConfig(
                    endpoint="https://vmstore1.example.com",
                    username="admin",
                    password="secret123",
                )
            ],
        )
        
        with pytest.raises(ValueError, match="TGC endpoint is required"):
            config.validate()
