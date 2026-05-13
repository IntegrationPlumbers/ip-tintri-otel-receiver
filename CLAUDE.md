# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based OpenTelemetry Collector Receiver for monitoring Tintri storage infrastructure (VMstore appliances and Tintri Global Center). Collects performance, capacity, and health metrics from Tintri APIs and exports them via OTLP.

## Commands

```bash
# Install (uses uv)
uv pip install -e .
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run single test file
pytest tests/test_vmstore_client.py -v

# Run with coverage
pytest tests/ --cov=tintri_receiver --cov-report=term-missing --cov-report=html

# Lint & format
flake8 src/tintri_receiver tests/ --max-line-length=100 --ignore=E203,W503
black src/tintri_receiver tests/ --line-length=88
mypy src/tintri_receiver --ignore-missing-imports

# Run receiver
tintri-receiver --config config.yaml
tintri-receiver --config config.yaml --validate
```

## Architecture

**Single-endpoint collection model:** All HTTP traffic goes to the TGC. VMstore appliances are never contacted directly — instead, VMstore-scoped paths (e.g. `/datastore/{vmstoreUuid}/statsRealtime`) are served by the TGC keyed off the VMstore UUID. TGC config is required.

- **TGC inventory tier** (slow, 5-15 min) — `tgc_client.py` + `tgc_inventory.py` — calls `GET /vmstore` to discover infrastructure, caches inventory, resolves VMstore UUIDs from hostnames/IPs, provides attribute enrichment.
- **VMstore metrics tier** (fast, 30-60 sec) — `vmstore_client.py` + `vmstore_collector.py` — collects real-time performance/capacity metrics. The `VMstoreRestClient` is instantiated with the TGC's base URL and credentials.

**API endpoint ownership:**
- `GET /vmstore` is TGC-only; called by `TGCRestClient`.
- `GET /datastore/{uuid}` only accepts the literal `default` as the path segment — passing a real UUID returns 400. Each VMstore exposes a single datastore through this alias.
- Stats sub-endpoints (`/datastore/{uuid}/statsRealtime`, `/statsSummary`) take the **VMstore UUID** as the path parameter, not the datastore UUID.

**Data flow:**
- `config.py` — dataclass-based YAML config parsing with env var resolution (`${env:VAR}`)
- `vmstore_client.py` — REST client for the VMstore-scoped endpoint surface (session auth, retry logic). At runtime, this client is constructed against the TGC's base URL and credentials, so requests go to the TGC. No `/vmstore` endpoint.
- `tgc_client.py` — REST client for TGC-only endpoints (has `get_vmstores()` for `/vmstore`)
- `tgc_inventory.py` — background inventory manager, provides attribute lookups and `get_vmstore_info()` to resolve VMstore UUIDs from hostnames/IPs in the cached `/vmstore` response
- `vmstore_collector.py` — orchestrates per-VMstore collection. `_resolve_datastores()` fetches `/datastore/default`; `_stats_path_uuid()` resolves the VMstore UUID used by stats sub-endpoints (prefers TGC-resolved UUID, falls back to `datastore.vmstoreUuid` or the datastore's own UUID).
- `metric_transformer.py` — static methods converting raw API responses into metric dicts (`{name, value, unit, attributes}`)
- `receiver.py` — top-level orchestrator, sets up OTel MeterProvider, manages collection threads, exports via OTLP
- `cli.py` / `src/cli.py` — CLI entry point with signal handling

**Metric dict format** (internal interchange between collector and exporter):
```python
{"name": "tintri.vm.latency.read", "value": 1.5, "unit": "ms", "attributes": {"tintri.vm.uuid": "..."}}
```

## Key Design Decisions

- TGC is required — the receiver routes all VMstore API calls through the TGC and raises on startup if `tgc` config is missing
- Gauges are cached in `TintriReceiver._gauges` dict to avoid recreating OTel instruments
- System metrics collection is currently commented out in `vmstore_collector.py`
- Alert collection is commented out (only applies to TGC)
- VDISK capacity collection is off by default (slower API calls)
- The receiver uses threading (not asyncio) for concurrent VMstore collection

## Test Markers

```bash
pytest -m "not slow"        # skip slow tests
pytest -m "integration"     # integration tests only
pytest -m "unit"            # unit tests only
```
