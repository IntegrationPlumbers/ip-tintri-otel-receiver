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

**Two-tier collection model:**
1. **TGC tier** (slow, 5-15 min) — `tgc_client.py` + `tgc_inventory.py` — calls `GET /vmstore` (TGC-only) to discover infrastructure, caches inventory, resolves datastore UUIDs, provides attribute enrichment
2. **VMstore tier** (fast, 30-60 sec) — `vmstore_client.py` + `vmstore_collector.py` — collects real-time performance/capacity metrics per VMstore

**API endpoint ownership:** `GET /vmstore` is TGC-only. VMstore appliances expose `/datastore`, `/vm`, `/virtualDisk` and their sub-resources (e.g. `/datastore/{uuid}/statsRealtime`). The `VMstoreRestClient` must never call `/vmstore`.

**Data flow:**
- `config.py` — dataclass-based YAML config parsing with env var resolution (`${env:VAR}`)
- `vmstore_client.py` — REST client for VMstore API v3.10 (session auth, retry logic). No `/vmstore` endpoint.
- `tgc_client.py` — REST client for TGC API (has `get_vmstores()` for `/vmstore`)
- `tgc_inventory.py` — background inventory manager, provides attribute lookups and `get_datastore_ids_for_vmstore()` to resolve datastore UUIDs from cached `/vmstore` response
- `vmstore_collector.py` — orchestrates per-VMstore collection. `_resolve_datastores()` uses TGC for datastore UUID lookup when available, falls back to VMstore `GET /datastore` when not.
- `metric_transformer.py` — static methods converting raw API responses into metric dicts (`{name, value, unit, attributes}`)
- `receiver.py` — top-level orchestrator, sets up OTel MeterProvider, manages collection threads, exports via OTLP
- `cli.py` / `src/cli.py` — CLI entry point with signal handling

**Metric dict format** (internal interchange between collector and exporter):
```python
{"name": "tintri.vm.latency.read", "value": 1.5, "unit": "ms", "attributes": {"tintri.vm.uuid": "..."}}
```

## Key Design Decisions

- TGC is optional — receiver degrades gracefully without it (metrics lack enriched attributes)
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
