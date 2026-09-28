# Universal Log Pre-processing Framework (ULPF)

> Any Log. Any Source. One Unified, Traceable Event Model.

A containerized, vendor-agnostic preprocessing layer that ingests heterogeneous security, network,
and application logs; detects their format; parses them through a pluggable parser architecture;
normalizes them into a versioned Universal Event Schema; preserves the original raw data; tracks
provenance and duplicates; and exposes analytics, data-lake, and ML-ready outputs.

ULPF is the preprocessing layer between heterogeneous log-producing systems and downstream
security, analytics, data-lake, and ML workloads. It does not attempt to replace a full SIEM, SOC
platform, threat-intelligence system, or incident-response platform.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start](#2-quick-start)
3. [Working Prototype Demo](#3-working-prototype-demo)
4. [Problem](#4-problem)
5. [Solution Overview](#5-solution-overview)
6. [Core Capabilities](#6-core-capabilities)
7. [Supported Log Formats](#7-supported-log-formats)
8. [Architecture](#8-architecture)
9. [End-to-End Processing Flow](#9-end-to-end-processing-flow)
10. [Parser Architecture](#10-parser-architecture)
11. [Universal Event Schema](#11-universal-event-schema)
12. [Data Integrity and Provenance](#12-data-integrity-and-provenance)
13. [Queue and Worker Architecture](#13-queue-and-worker-architecture)
14. [Storage Architecture](#14-storage-architecture)
15. [Analytics and ML-Ready Data](#15-analytics-and-ml-ready-data)
16. [Web Application](#16-web-application)
17. [Technology Stack](#17-technology-stack)
18. [Repository Structure](#18-repository-structure)
19. [Environment Configuration](#19-environment-configuration)
20. [Service Ports](#20-service-ports)
21. [API Overview](#21-api-overview)
22. [Data Export](#22-data-export)
23. [Custom Parser Onboarding](#23-custom-parser-onboarding)
24. [Testing](#24-testing)
25. [Operational Commands](#25-operational-commands)
26. [Scalability: Current State and Path](#26-scalability-current-state-and-path)
27. [Security and Deployment Posture](#27-security-and-deployment-posture)
28. [Requirement Coverage](#28-requirement-coverage)
29. [Known Limitations](#29-known-limitations)
30. [Troubleshooting](#30-troubleshooting)
31. [Screenshots](#31-screenshots)
32. [Contributing](#32-contributing)
33. [License and Authors](#33-license-and-authors)

---

## 1. Prerequisites

**Required**
- Docker Desktop
- Git

**Optional (local development outside Docker)**
- Python 3.11+
- Node.js 18+
- npm
- PostgreSQL client
- curl

Docker is the recommended path — it provisions the complete multi-service environment
(frontend, backend, database, queue, object storage, worker) in one command.

---
## 2. Quick Start

```bash
git clone https://github.com/Sayan4496/UPLS.git
cd UPLS/universal-log-framework
docker compose up -d --build
```

Verify:
```bash
docker compose ps
```
All services should show `Up` (and `healthy` where a healthcheck is configured): frontend,
backend, database, redpanda, minio, ulpf-worker, ulpf-datalake-exporter.

Open:

| Service | URL |
|---|---|
| Frontend Dashboard | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger API Documentation | http://localhost:8000/docs |

---
## 3. Working Prototype Demo

A recorded walkthrough of the running system — upload, processing, dashboard, analytics, and
export — is available here:

**[Watch the working prototype demo](https://www.youtube.com/watch?v=FPuIGO15iRE)**


---
## 4. Problem

Modern environments generate logs from firewalls, network devices, servers, operating systems,
applications, databases, cloud platforms, containers, and security tools — each in a different
shape: Syslog, JSON, CSV, XML, CEF, LEEF, key-value, or a vendor-specific schema. The same
semantic field routinely appears under different names across sources:

```
src
source_ip
src_ip
sourceAddress
```

Before any meaningful analytics, correlation, threat hunting, or ML can run on this data, a
downstream platform has to solve, for every new source:

- Detect the source format
- Parse heterogeneous records
- Normalize inconsistent field names and values
- Preserve the original event for forensics/compliance
- Track provenance and parser information
- Handle duplicates and malformed records
- Produce a consistent structure for analytics and ML
- Support batch and asynchronous processing at volume
- Provide a path from raw data into data-lake storage

ULPF exists to solve this preprocessing layer once, generically, instead of once per source per
downstream platform.

---
## 5. Solution Overview

ULPF provides one pipeline: **ingest → detect → parse → normalize → preserve → persist →
export/analyze.**

```
                    ┌───────────────────────┐
                    │       User / API      │
                    └───────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
              File Upload           Direct Ingestion
              Batch / Large             Event API
                    │                       │
                    └───────────┬───────────┘
                                ▼
                         ┌────────────┐
                         │  FastAPI   │
                         └─────┬──────┘
                               │
                               ▼
                         ┌────────────┐
                         │   MinIO    │
                         │ Raw Object │
                         └─────┬──────┘
                               │
                         object reference
                               │
                               ▼
                         ┌────────────┐
                         │ Redpanda   │
                         │ Event Queue│
                         └─────┬──────┘
                               │
                               ▼
                         ┌────────────┐
                         │   Worker   │
                         └─────┬──────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Parser Registry   │
                    └──────────┬──────────┘
                               │
                         detect + select
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Parser        │
                    │ Syslog / JSON / CSV │
                    │ XML / CEF / LEEF/KV │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Normalization    │
                    │  Universal Event    │
                    │       Schema        │
                    └──────────┬──────────┘
                               │
                    raw + provenance + dedup
                               │
                     ┌─────────┴─────────┐
                     ▼                   ▼
               ┌───────────┐       ┌───────────┐
               │ PostgreSQL│       │   MinIO   │
               │ Events /  │       │  Parquet  │
               │ Jobs /    │       │ Data Lake │
               │ Features  │       └───────────┘
               └─────┬─────┘
                     │
                     ▼
        ┌──────────────────────────────────┐
        │ Dashboard / Events / Analytics / │
        │ History / Reports / ML Dataset   │
        └──────────────────────────────────┘
```

The architecture separates four planes:

| Plane | Responsibility |
|---|---|
| **Control plane** | API, job creation, configuration, metadata |
| **Data plane** | Raw objects, queue messages, parser/normalization processing |
| **Storage plane** | PostgreSQL and object storage |
| **Presentation plane** | React dashboard and exports |

---
## 6. Core Capabilities

**Ingestion**
- File-based log upload (single and batch)
- API/event ingestion (`POST /api/v1/logs/ingest`)
- Queue-backed asynchronous processing
- Raw object storage through MinIO

**Detection and Parsing**
- Automatic format detection with a confidence score
- Parser registry with deterministic parser selection
- Built-in parsers for JSON, CSV, XML, CEF, LEEF, Syslog, Key-Value
- Parser confidence and fallback reporting
- Malformed-record accounting (skipped lines, parse errors)

**Normalization**
- Versioned Universal Event Schema
- Timestamp, IP, severity, and action normalization
- Source/device metadata retention
- Parser and normalizer provenance stamped onto every event

**Data Integrity**
- Raw event preservation, independent of normalization outcome
- Event hashing and canonical/duplicate tracking (`duplicate_of`)
- Explicit per-record processing status (accepted / duplicate / rejected)
- Parser version and normalization version tracking

**Processing**
- Redpanda-based asynchronous queue
- Consumer-group worker with manual offset commits
- Retry handling for transient infrastructure failures
- Dead-letter queue (DLQ) for poison messages
- Job status tracking (`queued` → `processing` → `done` / `failed` / `dead_letter`)

**Analytics**
- Event statistics, volume-over-time, severity distribution
- Parser coverage, source health, processing history

**Data and ML**
- Fixed-width event features, persisted separately from normalized events
- Time-based rollups
- NDJSON ML dataset export
- Partitioned Parquet data-lake export

---
## 7. Supported Log Formats

| Format | Parser | Typical Use |
|---|---|---|
| Syslog | `SyslogParser` | Linux/network/security devices |
| JSON | `JSONParser` | APIs, applications, cloud systems |
| CSV | `CSVParser` | Batch exports |
| XML | `XMLParser` | Structured application/device data |
| CEF | `CEFParser` | Security products |
| LEEF | `LEEFParser` | Security products |
| Key-Value | `KeyValueParser` | Vendor/application logs |

The parser registry is responsible for discovery and selection, so adding a new format does not
require hard-coding it into the ingestion path — see [§23 Custom Parser Onboarding](#23-custom-parser-onboarding).

---
## 8. Architecture

**Presentation layer** — React + Vite dashboard and operator interface.

**API layer** — FastAPI: upload, events, analytics, Parser Lab, export, health.

**Processing layer** — Redpanda (async transport) + Worker (background processing) + Parser
Registry (discovery/selection) + Parsers (format-specific) + Normalization (universal schema).

**Persistence layer** — PostgreSQL: transactional/application/event storage.

**Object/data-lake layer** — MinIO (raw objects + Parquet data lake).

```
┌──────────────────────────────────────────────────────────────┐
│                        Presentation                           │
│                 React + Vite Web Application                 │
└──────────────────────────────┬───────────────────────────────┘
                               │ REST
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                         API Layer                             │
│                         FastAPI                              │
│  Upload │ Events │ Analytics │ Parser Lab │ Export │ Health │
└──────────────┬───────────────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
   MinIO            PostgreSQL
 Raw Objects       Metadata / Events
       │                ▲
       │                │
       ▼                │
   Redpanda ───────► Worker
                        │
                        ▼
                Parser Registry
                        │
                        ▼
                  Format Parser
                        │
                        ▼
                  Normalization
                        │
                        ├──────────► PostgreSQL
                        │
                        └──────────► MinIO / Parquet
```

| Component | Responsibility |
|---|---|
| React/Vite | Dashboard and operator interface |
| FastAPI | API, ingestion, queries, exports |
| Redpanda | Asynchronous event/job transport |
| Worker | Background processing |
| Parser Registry | Parser discovery and selection |
| Parsers | Format-specific parsing |
| Normalization Engine | Universal event conversion |
| PostgreSQL | Transactional application/event storage |
| MinIO | Raw object storage and data-lake storage |
| Parquet Exporter | Analytics-oriented data-lake output |

**Why each infrastructure component exists:**
- **Redpanda** decouples ingestion from long-running processing, so large-file processing is not
  tightly coupled to the HTTP request lifecycle.
- **MinIO** stores raw files so queue messages carry references rather than embedding large file
  contents.
- **Worker** performs asynchronous processing outside the HTTP request/response cycle, running
  existing synchronous processing logic in a way that does not block the async consumer loop.
- **PostgreSQL** stores transactional and query-oriented state.
- **Parquet** provides a columnar representation suited to analytical/data-lake workloads,
  separate from the transactional database.

---
## 9. End-to-End Processing Flow

### 6.1 File Upload

```
User → React Upload UI → POST /upload/ → FastAPI
  ├── persist upload/job metadata
  ├── store raw file in MinIO
  └── publish object reference → Redpanda → Worker
                                              │
                                              ▼
                                    download raw object
                                              │
                                              ▼
                                     Parser Registry → Parser
                                              │
                                              ▼
                                       Normalize events
                                              │
                                 Raw + normalized + provenance
                                        ┌───┴────┐
                                        ▼        ▼
                                   PostgreSQL   Parquet
                                        │
                                        ▼
                          Dashboard / Analytics / Reports
```

### 6.2 Direct Event Ingestion

```
External System / API Client
            │
            ▼
      POST /api/v1/logs/ingest
            │
            ▼
          FastAPI
            │
            ▼
       Processing Path
            │
            ▼
 Parser → Normalize → Persist → Analytics
```

Use file upload for batch/large-file testing; use API ingestion for event-oriented integration.

---
## 10. Parser Architecture

ULPF uses a common parser abstraction (`backend/parsers/base.py`). The registry:

- Discovers built-in parsers (`backend/parsers/builtin/`)
- Discovers filesystem-based custom parsers (`backend/parsers/custom/`)
- Evaluates each parser's detection logic and confidence
- Selects the best match with deterministic tie-breaking
- Exposes parser metadata to the API and Parser Lab

**Parser failure contract.** Every parser returns:

```
events
skipped_line_count
parse_errors
```

This lets the worker and UI distinguish successful parsing, skipped/malformed records, parser
errors, and unsupported input. **A non-empty input that produces zero events is treated as a
processing failure**, not silently reported as successful parsing.

---
## 11. Universal Event Schema

Different input formats map to one common representation:

```json
{
  "schema_version": "1.1.0",
  "event_timestamp": "2026-09-22T10:30:00Z",
  "source_ip": "192.168.1.10",
  "destination_ip": "10.0.0.5",
  "source_port": 44321,
  "destination_port": 443,
  "severity": "HIGH",
  "event_type": "NETWORK_CONNECTION",
  "action": "BLOCKED",
  "device_type": "firewall",
  "vendor": "example",
  "message": "Firewall blocked suspicious connection"
}
```

The exact fields populated depend on the source data. The property that matters: downstream
consumers query standardized fields without needing to know every vendor's original naming
convention.

---
## 12. Data Integrity and Provenance

ULPF deliberately separates raw evidence from normalized representation.

- **Raw event** — retained for forensic analysis, compliance, parser debugging, reprocessing,
  and provenance, independent of what normalization produces.
- **Normalized event** — optimized for search, analytics, correlation, visualization, and
  downstream ML.
- **Provenance** — every normalized event retains `schema_version`, `parser_used`,
  `parser_version`, `normalization_version`, `source_format`, `detection_confidence`, and
  `processing_status`.

```
Original Event → Detected Format → Parser + Version → Normalized Event → Analytics / Export
```

**Duplicate handling.** ULPF does not enforce a global unique constraint on the raw event hash;
duplicates are preserved rather than dropped:

```
Event Hash
   ├── Canonical event      is_duplicate = false, processing_status = accepted
   ├── Duplicate            is_duplicate = true,  processing_status = duplicate, duplicate_of = canonical.id
   └── Additional duplicates...
```

This preserves repeated source events (useful for volume/frequency analysis) while keeping one
canonical record for correlation.

---
## 13. Queue and Worker Architecture

Redpanda is the Kafka-compatible event transport. It exists to separate ingestion from
processing:

```
HTTP request → persist metadata → publish reference → HTTP response
                                                              │
                                                              └──► Worker → long-running processing
```

**Message design.** Queue messages carry processing metadata and object references, not large raw
files:

```json
{
  "job_id": "...",
  "upload_id": "...",
  "object_key": "...",
  "source_format": "...",
  "metadata": {}
}
```

The worker retrieves the raw object from MinIO before parsing.

**Worker responsibilities:**
- Consume queue messages
- Retrieve the referenced raw object
- Invoke the processing service
- Persist processing results
- Commit offsets only after successful processing
- Retry retryable failures (e.g. transient database errors) without routing them to the DLQ
- Route poison/malformed messages to the DLQ
- Maintain job status

The worker runs the existing processing service in a way that does not block the asynchronous
consumer loop, so long-running parsing/normalization does not stall message consumption.

---
## 14. Storage Architecture

**PostgreSQL** — transactional and query-oriented data: upload metadata, processing jobs, raw
event records, normalized events, provenance, duplicate relationships, feature vectors, rollups,
application state.

**MinIO** — object-oriented storage: original uploaded files, raw objects referenced by queued
jobs, and data-lake output (Parquet datasets).

**Parquet data lake** — the exporter writes bounded Parquet batches for downstream analytics,
data engineering, model development, and offline processing, so the transactional database is not
forced to act as the only long-term analytical store.

---
## 15. Analytics and ML-Ready Data

ULPF does not train or deploy a model as part of the core pipeline — it produces data that a
downstream ML/analytics system can consume consistently. "ML-ready" is backed by concrete
artifacts:

- Every universal event carries a fixed, versioned `schema_version`, parser and normalizer
  provenance, detection confidence, and an explicit processing status for accepted, duplicate, and
  rejected records.
- `backend/analytics/features.py` produces fixed-width numeric feature columns: source type,
  severity, action, hour, day of week, and a 24-hour source event count — persisted separately in
  `normalized_event_features`, with hourly rollups updated once per processing batch (not per
  event).
- The data-lake worker writes bounded Parquet batches for downstream training/analytics workflows.
- `GET /api/v1/export/ml-dataset` streams the engineered feature rows as NDJSON, capped by the
  same configured export limit as other exports.

Example feature row:
```json
{
  "event_id": "...",
  "source_type": "SYSLOG",
  "severity": "HIGH",
  "hour": 14,
  "day_of_week": 2
}
```

---
## 16. Web Application

| Page | Purpose |
|---|---|
| **Dashboard** | Total events, severity breakdown, source activity, recent events, parser coverage, backend/database health |
| **Log Upload** | Single/batch file upload, processing status visibility |
| **Processing History** | Job ID, source file, detected format, record counts, quality issues, status, processing duration |
| **Events** | Normalized event exploration and provenance |
| **Parser Lab** | Registered parser formats, preview, detection/normalization preview, confidence |
| **Analytics** | Volume over time, severity distribution, parser coverage, source health |
| **Reports** | Bounded exports: JSON, CSV, NDJSON, ML dataset |
| **Devices** | Source/device inventory view |
| **Settings** | Display and preference configuration |

**Note on Processing History fields:** "Records" = parsed records; "Processed" = normalized
records; "Quality Issues" = normalization/quality flags (not database persistence failures);
"Status" = job state; "Time" = actual processing duration when available.

---
## 17. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend | Python 3.11 + FastAPI |
| ORM | SQLAlchemy |
| API Server | Uvicorn |
| Database | PostgreSQL 16 |
| Message Broker | Redpanda |
| Object Storage | MinIO |
| Data Lake Format | Parquet |
| Containerization | Docker + Docker Compose |
| Testing | pytest |
| API Documentation | OpenAPI / Swagger |

---
## 18. Repository Structure

```
UPLS/
│
├── backend/
│   ├── api/
│   │   ├── upload.py
│   │   ├── events.py
│   │   ├── analytics.py
│   │   ├── parser_lab.py
│   │   └── export.py
│   │
│   ├── app/
│   │   └── main.py
│   │
│   ├── analytics/
│   │   └── features.py
│   │
│   ├── core/
│   │
│   ├── detection/
│   │   └── format_detector.py
│   │
│   ├── datalake/
│   │   └── exporter.py
│   │
│   ├── ingestion/
│   │   └── processing_service.py
│   │
│   ├── models/
│   │   ├── raw_event.py
│   │   ├── normalized_event.py
│   │   └── ...
│   │
│   ├── normalization/
│   │   └── service.py
│   │
│   ├── parsers/
│   │   ├── base.py
│   │   ├── builtin/
│   │   └── custom/
│   │
│   ├── registry/
│   │   └── parser_registry.py
│   │
│   ├── ulpf_queue/
│   │   ├── producer.py
│   │   └── consumer.py
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── services/
│   │   └── ...
│   ├── package.json
│   └── Dockerfile
│
├── database/
│   ├── init.sql
│   └── migrations/
│
├── tests/
│   ├── test_parsers.py
│   ├── test_deduplication.py
│   └── test_worker_contracts.py
│
├── sample_logs/
│
├── docker-compose.yml
├── requirements-dev.txt
└── README.md
```

---
## 19. Environment Configuration

The development Compose configuration provides required values directly in `docker-compose.yml`
so no manual `.env` file is required to get started:

```yaml
POSTGRES_USER: postgres
POSTGRES_PASSWORD: postgres
POSTGRES_DB: ulpf_database
```

```
DATABASE_URL: postgresql+psycopg2://postgres:postgres@database:5432/ulpf_database
```

Queue-enabled uploads store the raw file in the MinIO bucket and send only the upload reference
and processing metadata through Redpanda; the worker retrieves the object before invoking the
existing parser and processing pipeline. This avoids embedding raw file content in a Redpanda
message. Keep the asynchronous path enabled with:

```
QUEUE_ENABLED=true
```

Queue and object-storage configuration should point to Compose service names (`redpanda`,
`minio`) rather than `localhost` for container-to-container communication.

> **Production guidance:** do not use development credentials in production. Move secrets to
> environment variables, Docker secrets, Kubernetes Secrets, or an equivalent secret-management
> system. `.env.example` is included as a reference.

---
## 20. Service Ports

| Service | Container Port | Host Port |
|---|---|---|
| Frontend | 5173 | 5173 |
| FastAPI | 8000 | 8000 |
| PostgreSQL | 5432 | 5433 |
| Redpanda | 9092 | 9092 |
| MinIO API | 9000 | 9000 |
| MinIO Console | 9001 | 9001 |

Verify actual mappings with `docker compose ps`.

**Backend Dockerfile entry point** (a common source of a broken deployment if changed
incorrectly):
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
`main.py` lives inside `app/`, so the module path must be `app.main:app`, not `main:app` — see
[§30 Troubleshooting](#30-troubleshooting).

---
## 21. API Overview

| Endpoint | Purpose |
|---|---|
| `GET /health` | Backend/database health check |
| `POST /upload/` | Upload a single log file |
| `POST /upload/batch` | Create a processing job for one or more files |
| `GET /upload/jobs` | List processing jobs |
| `GET /upload/jobs/{job_id}` | Get a single job's status |
| `POST /api/v1/logs/ingest` | Event-oriented API ingestion |
| `GET /events/` | List/filter/search events (`severity`, `source_ip`, `destination_ip`, `event_type`, `search`, `page`, `limit`) |
| `GET /events/{event_id}` | Single event detail |
| `GET /events/stats` | Event statistics |
| `GET /analytics/dashboard` | Dashboard analytics |
| `GET /analytics/parser-coverage` | Parser coverage analytics |
| `GET /parser-lab/plugins` | Registered parser information |
| `GET /api/v1/export/ml-dataset` | ML-ready feature dataset export |

Additional JSON/CSV/NDJSON export routes are available through the Reports API. For exact
request/response schemas, use `http://localhost:8000/docs`.

---
## 22. Data Export

Supported representations: JSON, CSV, NDJSON, ML dataset NDJSON, and Parquet via the data-lake
exporter.

Exports stream rows from the database and are bounded by `MAX_EXPORT_RECORDS` (default: 100).
Bounding is intentional: large analytical datasets should use the Parquet/data-lake path rather
than a single API request materializing the entire event store.

**CSV** — Excel, Google Sheets, reporting.
**JSON** — API integration, automation, further programmatic analysis.
**NDJSON / ML dataset** — downstream feature consumption.

---
## 23. Custom Parser Onboarding

ULPF supports filesystem-based custom parser discovery — deliberately *not* arbitrary
runtime/browser-uploaded code execution, to avoid turning a parser-management feature into a
code-execution surface.

```
backend/
└── parsers/
    └── custom/
        └── my_parser/
            ├── __init__.py
            ├── parser.py
            └── manifest.yaml
```

A custom parser implements the shared `BaseParser` contract from `backend/parsers/base.py`. To
onboard one:

1. Add the parser to the filesystem under `backend/parsers/custom/`.
2. Provide its manifest/metadata.
3. Restart the backend/worker if required by your deployment.
4. Verify it appears in Parser Lab (`GET /parser-lab/plugins`).
5. Test detection and normalization before processing production data.

---
## 24. Testing

Sample log files are in `sample_logs/`. A focused pytest suite lives under `tests/`, with runtime
dependencies in `requirements-dev.txt`.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
```

**Current observed result: 16 passed, 3 failed, 2 skipped.**

- The 3 failures are intentional information about current behavior, not flaky tests: malformed
  CEF, LEEF, and Key-Value records currently return an empty list instead of raising or returning
  an explicit parse error (tracked — see [§29 Known Limitations](#29-known-limitations)).
- The 2 skipped tests are database-backed deduplication tests, skipped unless
  `TEST_DATABASE_URL` points to a dedicated test database. The fixture deliberately refuses to run
  against the live `DATABASE_URL`.

Coverage includes: JSON object/array/JSON Lines parsing, CSV, XML, Syslog parsing, empty and
header-only input, invalid UTF-8 rejection, worker DLQ/retry behavior, the lowercase job-status
contract, the frontend-consumed batch job payload shape, and database uniqueness behavior when a
dedicated test database is provided.

**This is not a full end-to-end test suite** — no browser flow, production-volume run, or
measured throughput run is claimed.

Additional validation:
```bash
python -m compileall backend
npm run build
npm run lint
git diff --check
```

Manual smoke test: start the containers → open the frontend → **Log Upload** → select a sample
file → **Upload & Process** → open **Events** to view normalized output. Sample formats: `.json`,
`.csv`, `.xml`, `.cef`, `.leef`, `.log`, `.txt`.

---
## 25. Operational Commands

```bash
# Start (no rebuild)
docker compose up -d

# Build and start
docker compose up -d --build

# Restart, preserving database/object-storage data
docker compose down
docker compose up -d

# Full destructive reset — deletes all volumes, including stored data
docker compose down -v --remove-orphans
docker compose up -d --build

# Status
docker compose ps

# Logs
docker logs ulpf-backend --tail 100
docker logs -f ulpf-backend
docker logs ulpf-worker --tail 100
docker logs -f ulpf-worker
docker logs ulpf-postgres --tail 100
docker logs redpanda --tail 100

# Remove orphan containers after changing docker-compose.yml
docker compose down --remove-orphans
docker compose up -d --build
```

---
## 26. Scalability: Current State and Path

**Implemented today:**
- Queue-decoupled ingestion through the Kafka-compatible producer/consumer in `backend/ulpf_queue/`.
- Consumer-group worker configuration (`backend/ulpf_queue/consumer.py`), allowing multiple
  worker instances to share partitions.
- Partitioned Parquet data-lake batches (`backend/datalake/exporter.py`).
- Built-in and filesystem-custom plugin parser discovery (`backend/registry/parser_registry.py`).

**Current throughput limits:**
- A single Kafka/Redpanda partition permits only one active consumer for that partition,
  regardless of worker replica count.
- Processing currently parses a full uploaded file in memory before normalization — not a
  streaming parser pipeline.
- HTTP exports are intentionally bounded by `MAX_EXPORT_RECORDS` and stream at most that many
  rows.
- **No throughput benchmark has been run.** Measured events-per-second and sustained-volume
  figures are **TODO** — ULPF does not claim a specific events-per-second or
  billions-of-events-per-day capability until a reproducible benchmark exists.

**Concrete path beyond current limits:**
1. Increase topic partitions and validate partition-key distribution before adding worker
   replicas.
2. Add bounded/chunked file parsing and batch-level backpressure instead of loading complete
   files.
3. Benchmark ingestion, normalization, queue lag, database writes, Parquet export, and bounded API
   export separately.
4. Use those measurements to size database connection pools, batch sizes, consumer concurrency,
   and data-lake partition sizes.

---
## 27. Security and Deployment Posture

ULPF is currently a **prototype/hackathon-oriented deployment**.

**Current posture:**
- No application authentication/authorization layer.
- Development database and MinIO credentials are used by default in Compose.
- Custom parsers are filesystem-based, not arbitrary uploaded/executed code.
- Docker Compose is the primary deployment method; core processing runs as isolated containers.

**Production hardening roadmap (not yet implemented):** authentication, authorization/RBAC, TLS,
secret management, credential rotation, audit logging, network policies, container image
scanning, dependency scanning, resource limits, rate limiting, stricter API request validation,
observability, backup/restore procedures, retention policies.

---
## 28. Requirement Coverage

This table records repository evidence, not intended future behavior. "Implemented" means the
code path exists — it does not imply production-scale or full end-to-end verification.

| Requirement | Status | Evidence |
|---|---|---|
| (a) Heterogeneous log ingestion | Implemented | `backend/api/upload.py` — single and batch uploads |
| (b) Automatic format detection | Implemented | `backend/registry/parser_registry.py` exposes `detect_best_parser` |
| (c) JSON/CSV/XML/CEF/LEEF/Syslog/Key-Value parsers | Partial | Built-ins exist under `backend/parsers/builtin/`; malformed CEF/LEEF/Key-Value inputs currently fail focused tests by returning empty results |
| (d) Common normalized event storage | Implemented | `backend/models/normalized_event.py`, `backend/normalization/service.py` |
| (e) Queue-decoupled worker processing | Implemented | `backend/ulpf_queue/producer.py` publishes references; `consumer.py` processes them |
| (f) Poison-message DLQ and retry separation | Implemented | `consumer.py` separates `PoisonMessageError` from `RETRYABLE_ERRORS`; covered by focused tests |
| (g) Batch upload job tracking | Implemented | `POST /upload/batch` returns a job payload; `GET /upload/jobs/{job_id}` returns status |
| (h) Fixed-width ML feature persistence | Partial | `backend/analytics/features.py` + `normalized_event_features` exist; dedicated Postgres tests skipped without `TEST_DATABASE_URL` |
| (i) Parquet data-lake export | Implemented | `backend/datalake/exporter.py` writes partitioned Parquet batches |
| (j) Bounded streaming event exports | Implemented | `backend/api/export.py` — JSON/CSV/NDJSON + `/api/v1/export/ml-dataset`, bounded by `MAX_EXPORT_RECORDS` |
| (k) Authentication / production security posture | Designed, not built | No authentication layer present; deployment remains a prototype posture |

---
## 29. Known Limitations

- **No authentication or authorization layer.**
- **Custom plugins are filesystem-only**, discovered from `backend/parsers/custom/` — this is a
  deliberate security choice, not a missing feature.
- **Development credentials** are used by default in Docker Compose (PostgreSQL, MinIO).
- **Large-file memory behavior:** processing is not a fully streaming parser pipeline; very large
  files may need more memory than a chunked implementation would use.
- **No sustained production-scale throughput benchmark is claimed.**
- **Malformed CEF/LEEF/Key-Value records currently return an empty result** rather than an
  explicit parse error — tracked by the 3 known test failures in [§24 Testing](#24-testing).
- **Queue recovery:** the worker has recovery handling for long-running processing and
  consumer/commit failures, but live queue recovery should still be validated after any
  deployment change before treating the environment as production-ready.
- **Event time vs. processing time:** analytics use the event's own timestamp for time-based
  aggregation, so `upload date ≠ processing date ≠ event date`. An event uploaded on September 23
  can legitimately appear under September 22 if that's its original event timestamp — this
  matters for forensic and historical analytics and is not a bug.

---
## 30. Troubleshooting

**Backend not reachable on port 8000**
```bash
docker compose ps
docker logs ulpf-backend --tail 100
```

**`Could not import module "main"`** — the Dockerfile's Uvicorn command points to the wrong
module path.
```dockerfile
# Incorrect
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# Correct — main.py lives inside app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
```bash
docker compose up -d --build backend
```

**Container name already in use**
```bash
docker compose down --remove-orphans
docker compose up -d
```

**Frontend cannot connect to backend**
1. `docker compose ps` should show the backend `Up`.
2. Open `http://localhost:8000/docs` directly — if Swagger loads, the backend is healthy.
3. Check the frontend's API base URL points to `http://localhost:8000`.

**Worker is not processing jobs**
```bash
docker logs ulpf-worker --tail 200
docker logs redpanda --tail 200
```
Confirm: Redpanda is healthy; `QUEUE_ENABLED=true`; the worker is connected to the correct
broker; the consumer group is assigned; consumer lag is decreasing; jobs are not repeatedly
entering retry/DLQ state. **Do not manually commit offsets merely to make the UI appear
healthy** — offset advancement should correspond to actual successful processing.

**Jobs remain queued** — look for `CommitFailedError`, `UnknownMemberIdError`, or
`NodeNotReadyError` in worker logs; these indicate queue/consumer-group coordination problems,
not a frontend issue. Restart the affected service only after confirming runtime state.

**Database connection problems**
```bash
docker logs ulpf-postgres --tail 100
docker compose ps
```
The backend should connect via the Docker service name `database:5432`, not the host-mapped port.

**Note on resets:** `docker compose down` alone preserves the database/object-storage volumes —
routine restarts don't lose data. To wipe everything, use
`docker compose down -v --remove-orphans`.

---
## 31. Screenshots

### Dashboard
<img width="1911" height="1075" alt="Screenshot 2026-09-25 134528" src="https://github.com/user-attachments/assets/d2b27b4d-fea6-47eb-9eb4-5a7372f41123" />

### Light Mode
<img width="3837" height="2295" alt="image" src="https://github.com/user-attachments/assets/e85e9cce-6083-4c5e-a078-12c175d7226c" />

### Log Upload
<img width="1916" height="1092" alt="Screenshot 2026-09-25 134610" src="https://github.com/user-attachments/assets/bfd22123-8021-4b79-b382-8c23e1586df0" />

### Events
<img width="1917" height="1091" alt="Screenshot 2026-09-25 134550" src="https://github.com/user-attachments/assets/bcd9807b-32a6-49a2-b62d-d575385fc903" />

### Analytics
<img width="3837" height="2297" alt="image" src="https://github.com/user-attachments/assets/d44f0957-7d76-4511-a295-44c57fe3b657" />

### Reports
<img width="1912" height="1087" alt="Screenshot 2026-09-25 134829" src="https://github.com/user-attachments/assets/17363174-8e71-45aa-a056-69fa45beb773" />

> Prefer repository-local images (e.g. `docs/images/*.png`) over externally hosted attachment
> URLs once available, so the README stays portable.

---
## 32. Contributing

```bash
git checkout -b feature/<short-description>
# make the change, add/update tests
python -m pytest -q tests
python -m compileall backend
npm run build
npm run lint
git diff --check
git add .
git commit -m "feat: describe the change"
git push origin feature/<short-description>
```
Open a Pull Request.

**Principles:**
- Preserve raw data.
- Keep parser behavior deterministic.
- Avoid vendor-specific coupling in the core pipeline.
- Maintain backward compatibility of API contracts where possible.
- Add tests for parser and processing changes.
- Do not introduce arbitrary runtime code execution.
- Document architectural changes.
- Avoid claiming performance characteristics without a benchmark.

---
## 33. License and Authors

License information has not yet been added to this repository.

Developed by Sayan Deyashi and the ULPF development team.
Repository: [github.com/Sayan4496/UPLS](https://github.com/Sayan4496/UPLS)

**Project status:** ULPF is an active prototype/hackathon implementation, designed as a reusable
preprocessing layer between heterogeneous log-producing systems and downstream security,
analytics, data-lake, and ML workloads.
