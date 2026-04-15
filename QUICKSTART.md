# Tintri OpenTelemetry Receiver - Quick Start Guide

## Immediate Next Steps

### 1. Install Dependencies

```bash
cd ip-tintri-otel-receiver

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package
uv pip install -e .

# Or install with dev dependencies
uv pip install -e ".[dev]"
```

### 2. Configure Your Tintri Environment

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit with your Tintri details
nano config.yaml  # or vim, code, etc.
```

Update these sections:
- `tgc.endpoint`: Your TGC URL
- `vmstores[].endpoint`: Your VMstore URLs
- Set passwords as environment variables

### 3. Set Credentials

```bash
export TGC_PASSWORD="your-tgc-password"
export VMSTORE1_PASSWORD="your-vmstore1-password"
```

### 4. Validate Configuration

```bash
tintri-receiver --config config.yaml --validate
```

### 5. Run the Receiver

```bash
# Run with default logging
tintri-receiver --config config.yaml

# Run with debug logging
tintri-receiver --config config.yaml --log-level DEBUG
```

## Running Tests

```bash
# Install test dependencies
uv pip install pytest pytest-cov pytest-mock

# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=tintri_receiver --cov-report=html

# View coverage report
xdg-open htmlcov/index.html
```

## What's Implemented

### Active Collection
- Datastore metrics (performance, capacity, savings, replication)
- VM metrics (performance, capacity, CPU/memory, savings, QoS)
- VDISK performance metrics (latency, IOPS, throughput)
- VDISK capacity metrics (optional via config)
- TGC inventory and topology integration
- Attribute enrichment (tenant, application, hypervisor)
- Two-tier collection model (TGC slow / VMstore fast)
- Concurrent VMstore collection

### Disabled
- System-level metrics (collection call commented out, method exists)
- Alert collection (TGC-only, commented out)

### Not Implemented
- Integration tests with mock Tintri API
- Grafana dashboards
- Kubernetes manifests

## Architecture

```
+----------------------------------------------------+
|                  TintriReceiver                     |
|                   (orchestrator)                    |
+------------------+---------------------------------+
                   |
         +---------+---------+
         |                   |
    +----v-----+      +-----v--------+
    |   TGC    |      |   VMstore    |
    | Manager  |      |  Collectors  |
    | (slow)   |      |   (fast)     |
    +----+-----+      +-----+--------+
         |                   |
         |  Attributes       |  Metrics
         +----------+--------+
                    |
              +-----v------+
              |   OTEL     |
              |  Exporter  |
              +------------+
```

**TGC tier** resolves datastore UUIDs via `GET /vmstore` (TGC-only) and provides attribute enrichment from cached inventory.

**VMstore tier** collects real-time metrics from each VMstore. When TGC is available, it uses the resolved datastore UUIDs to call `GET /datastore/{uuid}`. Without TGC, it falls back to `GET /datastore`.

## Customization Tips

### Disable Collections You Don't Need

```yaml
vmstores:
  - endpoint: "https://vmstore1.example.com"
    collect_vdisks: false  # Skip VDISKs
    collect_vms: true
```

### Adjust Collection Intervals

```yaml
tgc:
  collection_interval: 600s  # 10 minutes instead of 5

vmstores:
  - collection_interval: 30s  # 30 seconds instead of 60
```

### Add Resource Attributes

```yaml
resource_attributes:
  tintri.site: "datacenter-west"
  tintri.environment: "production"
  team: "storage-team"
```

## Common Use Cases

### Monitor Single VMstore (no TGC)
```yaml
receivers:
  tintri:
    vmstores:
      - endpoint: "https://vmstore.example.com"
        username: "admin"
        password: "${env:PASSWORD}"
```

### Monitor Multiple VMstores with TGC
```yaml
receivers:
  tintri:
    tgc:
      endpoint: "https://tgc.example.com"
      username: "admin"
      password: "${env:TGC_PASSWORD}"
    vmstores:
      - endpoint: "https://vmstore1.example.com"
        username: "admin"
        password: "${env:VMSTORE1_PASSWORD}"
      - endpoint: "https://vmstore2.example.com"
        username: "admin"
        password: "${env:VMSTORE2_PASSWORD}"
```

### Performance-Focused (Skip Capacity)
```yaml
vmstores:
  - endpoint: "https://vmstore.example.com"
    collect_datastores: true
    collect_vms: true
    collect_vdisks: false
    vdisk_capacity_collection: false
```

## Troubleshooting

### Authentication Errors
- Verify credentials are correct
- Check network connectivity to Tintri endpoints
- Ensure API version matches your Tintri installation

### No Metrics Appearing
- Check logs for errors: `--log-level DEBUG`
- Verify collection toggles are enabled
- Ensure objects exist (VMs, datastores, etc.)

### High Memory Usage
- Reduce VDISK collection or disable it
- Increase collection intervals
- Reduce number of VMstores

### TGC Connection Issues
- Receiver will continue without TGC
- Metrics won't have tenant/application attributes
- Datastore collection falls back to VMstore `/datastore` endpoint

## Development Workflow

```bash
# Make changes
vim src/tintri_receiver/vmstore_client.py

# Run tests
make test

# Format code
make format

# Check types
make type-check
```

## Resources

- **CONTRIBUTING.md**: Development guidelines
- **Tintri API Docs**: https://tintri.github.io/tintri-rest-api/
- **OpenTelemetry Docs**: https://opentelemetry.io/
