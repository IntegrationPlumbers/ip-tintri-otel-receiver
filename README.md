# Tintri OpenTelemetry Receiver

A Python-based OpenTelemetry Collector Receiver for monitoring Tintri storage infrastructure (VMstore appliances and Tintri Global Center).

## Features

- **Complete Monitoring Coverage**: System, Datastore, VM, and VDISK metrics
- **TGC Integration**: Automatic inventory discovery and rich attribute decoration
- **Performance Optimized**: Two-tier collection model (fast metrics, slow topology)
- **Production Ready**: Comprehensive error handling, retry logic, and graceful degradation
- **Extensible**: Easy to add new metrics and customize collection behavior

## Prerequisites

- Python 3.9 or higher
- Tintri VMstore with API v3.10+
- Tintri Global Center (optional but recommended)
- API credentials with read-only access

## Installation

```bash
# Install from source
git clone https://github.com/example/tintri-otel-receiver.git
cd tintri-otel-receiver
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Configuration

Create a `config.yaml` file:

```yaml
receivers:
  tintri:
    # TGC Configuration (optional but recommended)
    tgc:
      endpoint: "https://tgc.example.com"
      username: "admin"
      password: "${env:TGC_PASSWORD}"
      api_version: "v310"
      collection_interval: 300s
      enable_fleet_metrics: true
      timeout: 30s
      insecure_skip_verify: false
    
    # VMstore Configuration
    vmstores:
      - endpoint: "https://vmstore1.example.com"
        username: "admin"
        password: "${env:VMSTORE1_PASSWORD}"
        api_version: "v310"
        collection_interval: 60s
        timeout: 30s
        collect_system: true
        collect_datastores: true
        collect_vms: true
        collect_vdisks: true
    
    # Resource attributes
    resource_attributes:
      tintri.site: "datacenter-east"
      tintri.environment: "production"

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
  
  logging:
    loglevel: info

service:
  pipelines:
    metrics:
      receivers: [tintri]
      exporters: [prometheus, logging]
```

## Usage

### Standalone Mode

```bash
# Set credentials as environment variables
export TGC_PASSWORD="your-tgc-password"
export VMSTORE1_PASSWORD="your-vmstore-password"

# Run the receiver
tintri-receiver --config config.yaml
```

### Integration with OpenTelemetry Collector

Add to your OTEL Collector configuration and deploy as a custom component.

## Collected Metrics

### System/VMstore Metrics
- `tintri.system.latency.{read,write}` - Read/write latency (ms)
- `tintri.system.iops.{read,write}` - Read/write IOPS
- `tintri.system.throughput.{read,write}` - Read/write throughput (MB/s)
- `tintri.system.capacity.{total,used,used.pct}` - Capacity metrics
- `tintri.system.{cpu,memory}.utilization` - Resource utilization (%)
- `tintri.system.health.status` - Health status
- `tintri.system.alerts.active` - Active alert count

### Datastore Metrics
- `tintri.datastore.latency.{read,write}` - Performance metrics
- `tintri.datastore.iops.{read,write}` - IOPS metrics
- `tintri.datastore.throughput.{read,write}` - Throughput metrics
- `tintri.datastore.capacity.*` - Capacity metrics
- `tintri.datastore.health.status` - Health status
- `tintri.datastore.alerts.active` - Active alerts

### VM Metrics
- `tintri.vm.latency.{read,write}` - Performance metrics
- `tintri.vm.iops.{read,write}` - IOPS metrics
- `tintri.vm.throughput.{read,write}` - Throughput metrics
- `tintri.vm.capacity.{provisioned,used,snapshot.used}` - Capacity metrics
- `tintri.vm.qos.status` - QoS status
- `tintri.vm.alerts.active` - Active alerts

### VDISK Metrics
- `tintri.vdisk.latency.{read,write}` - Performance metrics
- `tintri.vdisk.iops.{read,write}` - IOPS metrics
- `tintri.vdisk.throughput.{read,write}` - Throughput metrics

### TGC Fleet Metrics (Optional)
- `tintri.tgc.capacity.*` - Fleet-wide capacity
- `tintri.tgc.system.count` - Number of VMstores
- `tintri.tgc.health.status` - Fleet health
- `tintri.tgc.alerts.active` - Fleet-wide alerts

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tintri_receiver --cov-report=html

# Run specific test file
pytest tests/test_vmstore_client.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

## Architecture

The receiver uses a two-tier collection model:

1. **TGC Tier** (slow cadence, 5-15 min): Discovers infrastructure and builds topology cache
2. **VMstore Tier** (fast cadence, 30-60 sec): Collects real-time performance metrics

Metrics are enriched with TGC-derived attributes before export.

## Troubleshooting

### Authentication Failures
- Verify credentials are correct
- Check API version compatibility
- Ensure network connectivity to endpoints

### Missing Metrics
- Verify object collection is enabled in config
- Check VMstore API access permissions
- Review logs for API errors

### High Memory Usage
- Reduce number of VDISKs collected
- Increase collection intervals
- Disable VDISK capacity collection

### TGC Connection Issues
- Receiver will continue without TGC attributes
- Check TGC endpoint and credentials
- Verify TGC API version

## License

MIT License

## Contributing

Contributions are welcome! Please submit pull requests or open issues for bugs and feature requests.

## Support

For issues and questions, please open a GitHub issue or contact the engineering team.
