# Tintri OpenTelemetry Receiver

A Python-based OpenTelemetry Collector Receiver for monitoring Tintri storage infrastructure (VMstore appliances and Tintri Global Center).

## Features

- **Complete Monitoring Coverage**: Datastore, VM, and VDISK metrics
- **TGC Integration**: Automatic inventory discovery and rich attribute decoration
- **Performance Optimized**: Two-tier collection model (fast metrics, slow topology)
- **Production Ready**: Comprehensive error handling, retry logic, and graceful degradation

## Prerequisites

- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Tintri VMstore with API v3.10+
- Tintri Global Center (optional but recommended)
- API credentials with read-only access

## Installation

```bash
# Install from source
git clone https://github.com/IntegrationPlumbers/ip-tintri-otel-receiver.git
cd ip-tintri-otel-receiver
uv pip install -e .

# Install with development dependencies
uv pip install -e ".[dev]"
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

# Validate config only
tintri-receiver --config config.yaml --validate
```

### Integration with OpenTelemetry Collector

Add to your OTEL Collector configuration and deploy as a custom component.

## Collected Metrics

All metrics are derived from the Tintri REST API v3.10 DatastoreStat, VirtualMachineStat, and VDisk schemas. Metrics are only emitted when the corresponding field is present in the API response.

### Datastore Metrics

Collected from each datastore via realtime stats, stats summary, and capacity endpoints.

**Latency** (`ms`): `tintri.datastore.latency.{contention_ms, disk_ms, flash_ms, host_ms, mirror_ms, mirror_read_ms, mirror_write_ms, mirror_write_network_ms, network_ms, storage_ms, throttle_ms, total_ms, difference_from_max_in_set_ms}`

**IOPS** (`ops`): `tintri.datastore.iops.{read, write, total, normalized_read, normalized_write, normalized_total, week_maximum, week_minimum}`

**Throughput** (`MB/s`): `tintri.datastore.throughput.{read, write, total, cache_read, flash_miss, week_maximum, week_minimum}`

**Performance Reserve**: `tintri.datastore.performance_reserve.{actual, auto_allocated, change, change_percent, if_auto_allocated, if_pinned, pinned, remaining, used}`

**Capacity** (`GiB`): `tintri.datastore.capacity.{total, used, provisioned, remaining_physical, used_live, used_live_physical, used_physical, used_mapped, used_other, used_other_physical, used_change, used_change_physical, used_diff_from_max, used_diff_from_max_physical, used_snapshots_hypervisor, used_snapshots_hypervisor_physical, used_snapshots_tintri, used_snapshots_tintri_physical, used_replica_snapshots_logical, used_replica_snapshots_physical, logical_mapped_with_snapshots, logical_unique, thick_used, compressed_live, compressed_snapshot_only, live_logical_footprint}`

**Capacity Percentages** (`%`): `tintri.datastore.capacity.{used_percent, provisioned_percent, used_change_percent, used_physical_change_percent, thick_used_percent}`

**Capacity Remaining**: `tintri.datastore.capacity.remaining_days` (days)

**Quota**: `tintri.datastore.quota.{subscribed, provisioned_percent}`

**Savings Factors**: `tintri.datastore.savings.{clone_dedupe_factor, compression_factor, dedupe_factor, snapshot_factor, space_factor, space_factor_with_snapshots, total_with_thin_provisioning}`

**Replication** (incoming and outgoing): `tintri.datastore.replication.{incoming,outgoing}.{bytes_remaining, bytes_remaining_incoming, oneshot_progress, oneshot_time_remaining, path_count, throughput_incoming_logical, throughput_incoming_physical, throughput_logical, throughput_logical_per_day, throughput_physical, throughput_physical_per_day, time_remaining}`

**Counts**: `tintri.datastore.count.{disks, vms, repl_links, k8s_clusters, k8s_containers, k8s_deployments, k8s_pvcs, k8s_pvs, k8s_pods}`, `tintri.datastore.files.{max, count}`, `tintri.datastore.ntb_recovery.{count_a, count_b}`

**Other**: `tintri.datastore.flash.hit_percent`, `tintri.datastore.io.aligned_percent`, `tintri.datastore.latency.iops_percent`, `tintri.datastore.request_size` (KiB), `tintri.datastore.inactive`, `tintri.datastore.health.status`

### VM Metrics

Collected from each VM via realtime stats and the VM object.

**Latency** (`ms`): `tintri.vm.latency.{contention_ms, disk_ms, flash_ms, host_ms, mirror_ms, mirror_read_ms, mirror_write_ms, mirror_write_network_ms, network_ms, storage_ms, throttle_ms, total_ms, difference_from_max_in_set_ms}`

**IOPS** (`ops`): `tintri.vm.iops.{read, write, total, normalized_read, normalized_write, normalized_total}`

**Throughput** (`MB/s`): `tintri.vm.throughput.{read, write, total, cache_read, flash_miss}`

**CPU / Memory**: `tintri.vm.cpu.{percent, usage_mhz, ready_percent, swap_wait_percent}`, `tintri.vm.memory.{usage_mib, usage_percent}`

**Performance Reserve**: `tintri.vm.performance_reserve.{actual, auto_allocated, change, change_percent, if_auto_allocated, if_pinned, pinned, remaining, used}`

**Capacity** (`GiB`): `tintri.vm.capacity.{provisioned, used, used_change, used_change_physical, used_live, used_live_physical, used_physical, used_diff_from_max, used_diff_from_max_physical, used_snapshots_hypervisor, used_snapshots_hypervisor_physical, used_snapshots_tintri, used_snapshots_tintri_physical, compressed_live, compressed_snapshot_only, live_logical_footprint, logical_live_unshared, logical_snapshot_unshared, physical_live_unshared, physical_snapshot_unshared, snapshot.used, change_mb_per_day}`

**Capacity Percentages** (`%`): `tintri.vm.capacity.{used_change_percent, used_physical_change_percent}`

**Savings Factors**: `tintri.vm.savings.{clone_dedupe_factor, compression_factor, snapshot_factor, space_factor, space_factor_with_snapshots}`

**Other**: `tintri.vm.flash.hit_percent`, `tintri.vm.io.aligned_percent`, `tintri.vm.latency.iops_percent`, `tintri.vm.request_size` (KiB), `tintri.vm.inactive`, `tintri.vm.qos.status`

### VDISK Metrics

Collected from each virtual disk via realtime stats.

**Performance**: `tintri.vdisk.latency.{read, write}` (ms), `tintri.vdisk.iops.{read, write}` (ops), `tintri.vdisk.throughput.{read, write}` (MB/s)

**Capacity** (optional, enabled via `vdisk_capacity_collection: true`): `tintri.vdisk.capacity.{provisioned, used}` (GB)

### System Metrics (currently disabled)

System-level metrics are defined but collection is not currently enabled. These aggregate datastore stats and include VMstore health/resource utilization sourced from TGC inventory.

`tintri.system.{latency.read, latency.write, iops.read, iops.write, throughput.read, throughput.write, capacity.total, capacity.used, capacity.used.pct, health.status, cpu.utilization, memory.utilization}`

## Architecture

The receiver uses a two-tier collection model:

1. **TGC Tier** (slow cadence, 5-15 min): Discovers infrastructure via `GET /vmstore` on TGC, builds topology cache, provides datastore UUID resolution and attribute enrichment
2. **VMstore Tier** (fast cadence, 30-60 sec): Collects real-time performance metrics from each VMstore via `GET /datastore/{uuid}`, `GET /vm`, `GET /virtualDisk`

When TGC is configured, datastore UUIDs are resolved from the TGC inventory cache. Without TGC, the collector falls back to listing datastores directly from the VMstore.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=tintri_receiver --cov-report=html

# Run specific test file
uv run pytest tests/test_vmstore_client.py -v
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

## Troubleshooting

### Authentication Failures
- Verify credentials are correct
- Check API version compatibility
- Ensure network connectivity to endpoints

### Missing Metrics
- Verify object collection is enabled in config
- Check VMstore API access permissions
- Review logs for API errors (`--log-level DEBUG`)

### High Memory Usage
- Reduce number of VDISKs collected
- Increase collection intervals
- Disable VDISK capacity collection

### TGC Connection Issues
- Receiver will continue without TGC attributes
- Datastore collection falls back to VMstore `/datastore` endpoint
- Check TGC endpoint and credentials

## License

MIT License

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.
