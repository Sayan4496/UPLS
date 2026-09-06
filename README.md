# Universal Log Pre-processing Framework (ULPF)

A containerized framework for parsing, processing, normalizing, storing, and analyzing heterogeneous security and network logs.

The Universal Log Pre-processing Framework provides a centralized platform for ingesting logs from different sources and converting them into a normalized format for security monitoring and analysis.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Supported Log Formats](#supported-log-formats)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Log Processing Pipeline](#log-processing-pipeline)
- [Normalized Event Schema](#normalized-event-schema)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation Guide](#installation-guide)
- [Environment Configuration](#environment-configuration)
- [Accessing the Application](#accessing-the-application)
- [API Endpoints](#api-endpoints)
- [Event Export](#event-export)
- [Database Configuration](#database-configuration)
- [Docker Compose Configuration](#docker-compose-configuration)
- [Testing the Application](#testing-the-application)
- [Common Operations](#common-operations)
- [Troubleshooting](#troubleshooting)
- [Screenshots](#screenshots)
- [Contribution](#contribution)
- [License](#license)
- [Authors](#authors)

---

## Quick Start

```bash
git clone https://github.com/Sayan4496/UPLS.git
cd UPLS/universal-log-framework
docker compose up -d --build
```

Then open:

| Service                  | URL                          |
|---------------------------|-------------------------------|
| Frontend Dashboard        | http://localhost:5173        |
| Backend API                | http://localhost:8000        |
| Swagger API Documentation  | http://localhost:8000/docs   |

Check containers:
```bash
docker compose ps
```

---

## Features

- Upload heterogeneous log files
- Automatic log format detection
- Pluggable parser architecture
- Support for JSON, CSV, XML, CEF, LEEF, Syslog, and Key-Value logs
- Raw event extraction
- Common event normalization
- Timestamp normalization
- IP address normalization
- Severity normalization
- Action normalization
- PostgreSQL event storage
- REST API for event retrieval
- Event filtering and searching
- Event statistics and analytics
- Security monitoring dashboard
- Device monitoring
- CSV event export
- JSON event export
- Docker-based deployment
- FastAPI interactive API documentation

---

## Supported Log Formats

The framework currently supports automatic detection and parsing of the following log formats:

| Format    | Description                          |
|-----------|----------------------------------------|
| JSON      | JavaScript Object Notation logs       |
| CSV       | Comma-Separated Value logs            |
| XML       | Structured XML event logs             |
| CEF       | Common Event Format                   |
| LEEF      | Log Event Extended Format             |
| SYSLOG    | Standard system and network logs      |
| KEY-VALUE | `key=value` formatted logs            |

The system automatically detects the log format during upload and routes the file to the appropriate parser.

---

## Technology Stack

**Frontend**
- React
- Vite
- JavaScript / TypeScript
- Modern responsive dashboard UI

**Backend**
- Python 3.11
- FastAPI
- SQLAlchemy
- Uvicorn

**Database**
- PostgreSQL 16

**Containerization**
- Docker
- Docker Compose

---

## System Architecture

```
                        ┌─────────────────────┐
                        │      Frontend       │
                        │    React + Vite     │
                        │     Port: 5173      │
                        └──────────┬──────────┘
                                   │
                                   │ REST API
                                   │
                        ┌──────────▼──────────┐
                        │      Backend        │
                        │       FastAPI       │
                        │     Port: 8000      │
                        └──────────┬──────────┘
                                   │
                                   │ SQLAlchemy
                                   │
                        ┌──────────▼──────────┐
                        │     PostgreSQL      │
                        │   Database Storage  │
                        │   Host Port: 5433   │
                        └─────────────────────┘
```

### Expected Running Architecture

```
┌─────────────────────────────────────────────┐
│                 Docker Host                  │
│                                               │
│   ┌──────────────┐      Port 5173            │
│   │   Frontend   │◄──────────────── Browser  │
│   │  React/Vite  │                           │
│   └──────┬───────┘                           │
│          │                                    │
│          │ API Requests                       │
│          ▼                                    │
│   ┌──────────────┐      Port 8000            │
│   │   Backend    │◄──────────────── Browser  │
│   │   FastAPI    │                           │
│   └──────┬───────┘                           │
│          │                                    │
│          ▼                                    │
│   ┌──────────────┐                           │
│   │ PostgreSQL   │      Port 5433            │
│   │  Database    │                           │
│   └──────────────┘                           │
│                                               │
└───────────────────────────────────────────────┘
```

---

## Log Processing Pipeline

When a log file is uploaded, the system processes it through the following pipeline:

1. User uploads a log file.
2. The backend receives the file through the Upload API.
3. The format detector identifies the log format.
4. The parser registry selects the appropriate parser.
5. Raw log events are extracted.
6. Events are normalized into a common schema.
7. Normalized events are stored in PostgreSQL.
8. Events become available through REST APIs.
9. The React dashboard displays and analyzes the events.

### Processing Flow

```
Log File
   │
   ▼
Format Detection
   │
   ▼
Parser Registry
   │
   ├── JSON Parser
   ├── CSV Parser
   ├── XML Parser
   ├── CEF Parser
   ├── LEEF Parser
   ├── Syslog Parser
   └── Key-Value Parser
   │
   ▼
Raw Events
   │
   ▼
Normalization Engine
   │
   ▼
Normalized Event Schema
   │
   ▼
PostgreSQL Database
   │
   ▼
REST API
   │
   ▼
React Dashboard
```

---

## Normalized Event Schema

Different log formats use different field names. For example:

```
src
source_ip
src_ip
sourceAddress
```

may all represent the same information. The normalization layer converts heterogeneous log fields into a common schema, allowing logs from different vendors and formats to be queried using one common structure.

**Example normalized fields:**

| Field              | Description                        |
|---------------------|--------------------------------------|
| `event_timestamp`   | Time of the event                  |
| `source_ip`         | Source IP address                  |
| `destination_ip`    | Destination IP address             |
| `source_port`       | Source network port                |
| `destination_port`  | Destination network port           |
| `severity`          | Event severity                     |
| `event_type`        | Type of security event             |
| `action`            | Allowed, Blocked, Denied, etc.     |
| `device_type`       | Device category                    |
| `vendor`            | Log source vendor                  |
| `message`           | Event description                  |

---

## Project Structure

```
UPLS/
│
├── backend/
│   ├── api/
│   ├── app/
│   │   └── main.py
│   ├── core/
│   ├── detection/
│   ├── ingestion/
│   ├── models/
│   ├── normalization/
│   ├── parsers/
│   │   ├── base_parser.py
│   │   ├── cef_parser.py
│   │   ├── csv_parser.py
│   │   ├── json_parser.py
│   │   ├── keyvalue_parser.py
│   │   ├── leef_parser.py
│   │   ├── syslog_parser.py
│   │   └── xml_parser.py
│   ├── registry/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── database/
│
├── sample_logs/
│
├── docker-compose.yml
│
└── README.md
```

---

## Prerequisites

**Required**
- Docker Desktop
- Git

**Optional (for local development outside Docker)**
- Python 3.11+
- Node.js 18+

---

## Installation Guide

### 1. Clone the Repository

```bash
git clone https://github.com/Sayan4496/UPLS.git
cd UPLS
```

### 2. Docker Setup

The easiest way to run the complete project is using Docker Compose. It will automatically build and start:

- PostgreSQL database
- FastAPI backend
- React frontend
- Docker network

### 3. Start the Application

From the project root directory, run:

```bash
docker compose up -d --build
```

This command will:

- Build the backend Docker image
- Build the frontend Docker image
- Start the PostgreSQL database
- Create the Docker network
- Start all containers

### 4. Check Container Status

```bash
docker compose ps
```

Expected output — all services should show as `Up`:

```
NAME            SERVICE     STATUS
ulpf-backend    backend     Up
ulpf-frontend   frontend    Up
ulpf-postgres   database    Up
```

---

## Environment Configuration

The default Docker configuration does not require users to manually create a `.env` file. All required development environment values are configured inside `docker-compose.yml`, including:

```yaml
POSTGRES_USER: postgres
POSTGRES_PASSWORD: postgres
POSTGRES_DB: ulpf_database
```

and:

```
DATABASE_URL: postgresql+psycopg2://postgres:postgres@database:5432/ulpf_database
```

Therefore, after cloning the repository, users can start the complete application directly with:

```bash
docker compose up -d --build
```

> **Note:** For production deployments, sensitive values such as database passwords, API keys, and secret keys should be moved to environment variables or a `.env` file. The repository includes `.env.example` as a reference for future configuration.

---

## Accessing the Application

Once all containers are running:

| Service                 | URL                              |
|--------------------------|-------------------------------------|
| Frontend Dashboard       | http://localhost:5173            |
| Backend API              | http://localhost:8000            |
| FastAPI Swagger Docs     | http://localhost:8000/docs       |

---

## API Endpoints

### Health Check
```
GET /health
```
Checks whether the backend service is running correctly.

### Upload Logs
```
POST /upload/
```
Allows users to upload supported log files for processing.

### Get All Events
```
GET /events/
```
Supported query parameters:

- `severity`
- `source_ip`
- `destination_ip`
- `event_type`
- `search`
- `page`
- `limit`

Example:
```
GET /events/?severity=HIGH&page=1&limit=20
```

### Get Event Statistics
```
GET /events/stats
```
Returns statistics such as:

- Total events
- High severity events
- Medium severity events
- Low severity events

### Get Single Event
```
GET /events/{event_id}
```
Example:
```
GET /events/123
```

---

## Event Export

The Reports module allows users to export processed events for external analysis.

**Supported export formats:**

- CSV Event Export
- JSON Event Export

### CSV Export

Useful for:

- Microsoft Excel
- Google Sheets
- Data analysis tools
- Reporting

### JSON Export

Useful for:

- API integration
- Automation
- Security tools
- Further programmatic analysis

---

## Database Configuration

The application uses **PostgreSQL 16**.

**Default Docker credentials:**

| Variable            | Value           |
|---------------------|-------------------|
| `POSTGRES_USER`     | postgres        |
| `POSTGRES_PASSWORD` | postgres        |
| `POSTGRES_DB`       | ulpf_database   |

**Port mapping:**

| Location  | Port |
|-----------|------|
| Host      | 5433 |
| Container | 5432 |

**Connection from the host machine:**
```
postgresql://postgres:postgres@localhost:5433/ulpf_database
```

**Connection from the backend container (via Docker service name):**
```
postgresql+psycopg2://postgres:postgres@database:5432/ulpf_database
```

---

## Docker Compose Configuration

The project uses three services: `database`, `backend`, and `frontend`.

### Service Ports

| Service    | Internal Port | Host Port |
|------------|-----------------|-----------|
| Frontend   | 5173           | 5173      |
| Backend    | 8000           | 8000      |
| PostgreSQL | 5432           | 5433      |

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **Important:** The correct Uvicorn entry point is `app.main:app`, since `main.py` lives inside the `app/` directory. Using `main:app` instead will raise:
> ```
> ERROR: Error loading ASGI app.
> Could not import module "main".
> ```

---

## Testing the Application

Sample log files are available inside the `sample_logs/` directory.

You can test the application by:

1. Starting the Docker containers.
2. Opening the frontend dashboard.
3. Navigating to **Log Upload**.
4. Selecting a sample log file.
5. Clicking **Upload & Process**.
6. Opening the **Events** page to view normalized events.

**Example supported sample formats:**

- `.json`
- `.csv`
- `.xml`
- `.cef`
- `.leef`
- `.log`
- `.txt`

---

## Common Operations

**Start all services (no rebuild needed after initial setup):**
```bash
docker compose up -d
```

**Build and start all services:**
```bash
docker compose up -d --build
```

**Restart application (preserves database data):**
```bash
docker compose down
docker compose up -d
```

**Complete reset (removes containers, networks, and database data):**

> ⚠️ This permanently deletes all stored data in the PostgreSQL volume.

```bash
docker compose down -v --remove-orphans
docker compose up -d --build
```

**Check container status:**
```bash
docker compose ps
```

**View logs:**
```bash
docker logs ulpf-backend --tail 100
docker logs -f ulpf-backend        # live logs

docker logs ulpf-frontend --tail 100
docker logs ulpf-postgres --tail 100
```

**Rebuild after changing Dockerfiles, dependencies, or compose configuration:**
```bash
docker compose up -d --build
```

**Remove orphan containers** (helpful after changing `docker-compose.yml`):
```bash
docker compose down --remove-orphans
docker compose up -d --build
```

---

## Troubleshooting

### Backend cannot be reached on port 8000

Check container status:
```bash
docker compose ps
```
If the backend status shows `Restarting`, inspect the logs:
```bash
docker logs ulpf-backend --tail 100
```

### `Could not import module "main"`

**Cause:** The Dockerfile's Uvicorn command points to the wrong module path.

Incorrect:
```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Correct:
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Then rebuild just the backend:
```bash
docker compose up -d --build backend
```

### Container name already in use

Example error:
```
The container name "/ulpf-postgres" is already in use
```

Solution:
```bash
docker compose down --remove-orphans
docker compose up -d
```

### Frontend cannot connect to backend

1. Confirm the backend is running: `docker compose ps` should show `Up`.
2. Verify FastAPI directly by opening `http://localhost:8000/docs`. If Swagger loads, the backend is healthy.
3. Check the frontend's API base URL configuration and confirm it points to `http://localhost:8000`.

### Note on resets

`docker compose down` alone preserves the database volume — your data survives a routine restart. To wipe stored data as well (a true full reset), use `docker compose down -v --remove-orphans` as shown in [Common Operations](#common-operations).

---

## Screenshots

### Dashboard
<img width="3837" height="2297" alt="image" src="https://github.com/user-attachments/assets/c628b2e5-8bef-45c4-b979-79755d1e7e3c" />

## In Dark Mode
<img width="3837" height="2295" alt="image" src="https://github.com/user-attachments/assets/e85e9cce-6083-4c5e-a078-12c175d7226c" />


### Log Upload
<img width="3837" height="2300" alt="image" src="https://github.com/user-attachments/assets/ec3b775a-d3b4-439b-9abd-3ebdc9c58f49" />


### Events
<img width="3837" height="2300" alt="image" src="https://github.com/user-attachments/assets/869f3d75-2cd6-4bc8-86f5-d930494f2d8d" />


### Analytics
<img width="3837" height="2297" alt="image" src="https://github.com/user-attachments/assets/d44f0957-7d76-4511-a295-44c57fe3b657" />


### Reports
<img width="3837" height="2300" alt="image" src="https://github.com/user-attachments/assets/4eab61d5-b9c9-4d2c-a550-240e61cd965c" />


---

## Contribution

1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature/feature-name
   ```
3. Make your changes and test the application.
4. Commit your changes:
   ```bash
   git add .
   git commit -m "Add feature description"
   ```
5. Push your branch:
   ```bash
   git push origin feature/feature-name
   ```
6. Open a Pull Request.

---

## License

This project is developed as part of the Universal Log Pre-processing Framework (ULPF) initiative.

## Authors

Developed by Sayan Deyashi and the ULPF development team.
Repository: [github.com/Sayan4496/UPLS](https://github.com/Sayan4496/UPLS)
