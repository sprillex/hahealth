# Comprehensive Health Tracker (hahealth)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue?logo=python)](https://python.org)
[![SQLite3](https://img.shields.io/badge/Database-SQLite3-003B57?logo=sqlite)](https://sqlite.org)
[![Home Assistant](https://img.shields.io/badge/Integration-Home%20Assistant-41BDF5?logo=home-assistant)](https://www.home-assistant.io)
[![MQTT](https://img.shields.io/badge/Telemetry-MQTT-660066?logo=eclipsemosquitto)](https://mqtt.org)

A robust, multi-user health tracking backend and responsive web dashboard engineered with FastAPI and SQLite. It provides unified, privacy-first management for vitals (blood pressure, pulse, weight), physical exercise, macronutrient/micronutrient nutrition tracking, medication schedules and inventory, allergy/vaccination records, and bidirectional automation with Home Assistant via MQTT and Webhooks.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Prerequisites](#2-prerequisites)
3. [Installation & Setup](#3-installation--setup)
4. [Configuration](#4-configuration)
5. [Usage Guide](#5-usage-guide)
   - [Development & Production Server Execution](#development--production-server-execution)
   - [Systemd Service Management](#systemd-service-management)
   - [CLI Administration Commands & Sample Logs](#cli-administration-commands--sample-logs)
   - [Automated Application Updates (`update.sh`)](#automated-application-updates-updatesh)
6. [Architecture & Subsystems](#6-architecture--subsystems)
   - [Component Hierarchy](#component-hierarchy)
   - [Data Storage & Migrations](#data-storage--migrations)
   - [Telemetry & Home Assistant Integration](#telemetry--home-assistant-integration)
   - [AI Health Insights (Google Gemini)](#ai-health-insights-google-gemini)
   - [Frontend Client & Theme Engine](#frontend-client--theme-engine)
7. [API Reference Link](#7-api-reference-link)
8. [Troubleshooting & Diagnostics](#8-troubleshooting--diagnostics)

---

## 1. Project Overview

The **Comprehensive Health Tracker** (`hahealth`) acts as a centralized personal health ledger and edge-deployed integration hub. Designed for deployment on low-power servers, single-board computers (such as Raspberry Pi / Odroid running DietPi/Debian), or standard Linux servers, it bridges daily health metrics with smart home telemetry.

### Core Capabilities
- **Multi-User Isolation**: Granular user accounts with configurable BMR/TDEE targets, customized meal windows (Breakfast, Lunch, Dinner), schedule windows (Morning, Afternoon, Evening, Bedtime), and preferred unit systems (Metric vs. Imperial).
- **Vitals & Exercise Logging**: Track systolic/diastolic blood pressure, pulse, stress levels, weight progression, and physical activities with automated MET-based calorie burn calculations.
- **Nutrition v1 & v2 Engine**: Search cached nutrition data, query Open Food Facts on-demand, generate unique UPC barcodes for homemade items, track macros (Calories, Protein, Fat, Carbs, Fiber, Sodium) and micronutrients (Cholesterol, Sugars, Vitamin D, Calcium, Iron, Potassium), build multi-ingredient recipes, and manage staples.
- **Medication & Adherence Hub**: Schedule daily dose windows, enforce single-dose-per-window logging rules, maintain pill inventory with low-stock refill alerts, and associate medications with prescriber contacts.
- **Medical History & Compliance**: Log allergy profiles and vaccination histories with automatic compliance reports.
- **Home Assistant Synchronization**: Full MQTT auto-discovery sensors, bidirectional shopping list synchronization with Home Assistant To-Do items, and webhook ingestion endpoints.
- **AI-Powered Nutrition Analysis**: Native Google Gemini API (`gemini-2.5-flash`) integration to generate contextual dietary recommendations based on daily intake and pantry staples.
- **Administration & Security**: Role-based access control, persistent API key management for external automation, JWT bearer token lifecycle with transparent frontend refresh queues, and encrypted database backup/restore mechanics.

---

## 2. Prerequisites

### Hardware Requirements
- **Architecture**: `x86_64`, `armv7l`, or `aarch64` (Raspberry Pi 3B+/4/5, DietPi boards, Intel NUC, VPS).
- **Memory (RAM)**: Minimum 512 MB available RAM (1 GB+ recommended when running browser automated tests or multiple worker processes).
- **Disk Storage**: Minimum 200 MB free storage for application code, virtual environment, and SQLite database storage.

### Supported Operating Systems
- **Debian / Ubuntu / Linux Mint**: Debian 11 (Bullseye), Debian 12 (Bookworm), Ubuntu 20.04+, Linux Mint 20+.
- **DietPi**: Optimized for DietPi on SBCs (default operational path `/home/dietpi/hahealth`).
- **Other POSIX Platforms**: Compatible with FreeBSD and macOS with Python 3.9+.

### Runtime Dependencies
- **Python**: Version `3.9` through `3.12`.
- **System Packages**: `python3-pip`, `python3-venv`, `git`, `curl`, `sqlite3`.
- **Broker (Optional for Home Assistant)**: Mosquitto or any MQTT 3.1.1/5.0 broker.

### Required Permissions
- Standard non-root user permissions for application execution.
- `sudo` access required only for managing systemd services (`systemctl`) or binding to privileged ports (<1024).

---

## 3. Installation & Setup

Execute the following exact, non-interactive shell commands to install and initialize the application:

### Step 1: Install System Packages
On Debian, Ubuntu, Linux Mint, or DietPi:
```bash
sudo apt-get update -y && sudo apt-get install -y python3 python3-venv python3-pip git sqlite3 curl
```

### Step 2: Clone Repository
```bash
git clone https://github.com/sprillex/hahealth.git /home/dietpi/hahealth
cd /home/dietpi/hahealth
```
*(Adjust the target path according to your deployment user).*

### Step 3: Create & Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 4: Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Initialize SQLite Schema & Run Migrations
Initialize the database tables and apply all incremental migrations:
```bash
python3 -c "from app.database import init_db; init_db()"
python3 scripts/migrate_all.py
```

---

## 4. Configuration

The application reads runtime settings from environment variables and an optional `.env` file located at the repository root (`/home/dietpi/hahealth/.env`).

### Setting Up `.env`
Copy the template configuration file:
```bash
cp .env.example .env
```

### Environment Variables & Default Values

| Variable | Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `MQTT_BROKER` | `string` | `localhost` | Hostname or IP address of the MQTT Broker (e.g. `192.168.1.50`). |
| `MQTT_PORT` | `integer`| `1883` | Network port for MQTT broker connection. |
| `MQTT_USERNAME` | `string` | *(empty / none)* | Username for authenticated MQTT broker connection. |
| `MQTT_PASSWORD` | `string` | *(empty / none)* | Password for authenticated MQTT broker connection. |
| `MQTT_TOPIC_PREFIX` | `string` | `hahealth/log` | MQTT topic prefix for inbound health metric subscriptions. |
| `HASS_DISCOVERY_PREFIX` | `string` | `homeassistant` | Home Assistant MQTT discovery topic prefix. |
| `CUSTOM_NUTRITION_URL` | `string` | `http://localhost:8000` | Base URL used by internal services and Home Assistant hooks. |
| `GEMINI_API_KEY` | `string` | *(empty / none)* | Google AI Studio API key for nutrition analysis (`gemini-2.5-flash`). |

### Key Filesystem Paths

| Path | Purpose |
| :--- | :--- |
| `health_app.db` | Primary SQLite3 database storing all users, logs, medications, and caches. |
| `app/static/` | Web frontend assets (`index.html`, `app.js`, `style.css`, `gauge.css`). |
| `scripts/migrate_all.py` | Idempotent database schema migration runner. |
| `update.sh` | Orchestration script for non-interactive updates and branch switching. |
| `blueprints/` & `ha_blueprints/` | Automation YAML blueprints for Home Assistant integration. |

---

## 5. Usage Guide

### Development & Production Server Execution

#### Development Server (with Auto-Reload)
```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Production ASGI Server (Multi-Worker)
```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --access-log
```

Once running:
- Web Dashboard: `http://<server-ip>:8000/`
- Interactive API Documentation (Swagger UI): `http://<server-ip>:8000/docs`
- OpenAPI JSON Specification: `http://<server-ip>:8000/openapi.json`

---

### Systemd Service Management

To deploy `hahealth` as a continuous daemon managed by systemd on DietPi or Debian/Ubuntu:

1. **Create the service unit file:**
```bash
sudo tee /etc/systemd/system/hahealth.service > /dev/null << 'EOF'
[Unit]
Description=Comprehensive Health Tracker Backend & UI
After=network.target

[Service]
Type=simple
User=dietpi
WorkingDirectory=/home/dietpi/hahealth
EnvironmentFile=-/home/dietpi/hahealth/.env
ExecStart=/home/dietpi/hahealth/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
```

2. **Reload systemd, enable, and start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable hahealth
sudo systemctl start hahealth
```

3. **Verify service status:**
```bash
sudo systemctl status hahealth --no-pager
```

4. **Inspect live service logs:**
```bash
journalctl -u hahealth -f
```

---

### CLI Administration Commands & Sample Logs

The application includes an administrative command-line interface implemented in `app.cli`. Always ensure `PYTHONPATH=.` is set when running CLI commands.

#### 1. Create a User Account
```bash
PYTHONPATH=. ./.venv/bin/python -m app.cli create-user \
  --name "operator" \
  --password "CorrectHorseBatteryStaple!" \
  --weight 75.0 \
  --height 180.0 \
  --unit-system metric
```
**Sample Output:**
```text
User 'operator' created successfully with ID: 1
```

*(For Imperial measurements, specify `--weight 165.0 --height 71.0 --unit-system imperial`. The CLI automatically converts values to Metric for database persistence: `Stored as Metric: 74.84 kg, 180.34 cm`).*

#### 2. Grant Administrator Privileges
```bash
PYTHONPATH=. ./.venv/bin/python -m app.cli make-admin --user-id 1
```
**Sample Output:**
```text
Admin privileges granted to user operator (ID: 1).
```

To revoke administrator access:
```bash
PYTHONPATH=. ./.venv/bin/python -m app.cli make-admin --user-id 1 --revoke
```
**Sample Output:**
```text
Admin privileges revoked from user operator (ID: 1).
```

#### 3. Generate Persistent API Key (for Home Assistant)
```bash
PYTHONPATH=. ./.venv/bin/python -m app.cli create-apikey --user-id 1 --name "HomeAssistant"
```
**Sample Output:**
```text
API Key created for user operator.
Key Name: HomeAssistant
SECRET KEY (SAVE THIS NOW, IT WILL NOT BE SHOWN AGAIN): sec_key_7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c
```

#### 4. Revoke an API Key
```bash
PYTHONPATH=. ./.venv/bin/python -m app.cli revoke-apikey --key-id 1
```
**Sample Output:**
```text
API Key ID 1 revoked.
```

#### 5. Reset User Password
```bash
PYTHONPATH=. ./.venv/bin/python -m app.cli reset-password --user-id 1 --password "UpdatedSecurePassword99!"
```
**Sample Output:**
```text
Password reset for user operator (ID: 1).
```

---

### Automated Application Updates (`update.sh`)

The repository includes an operator update script (`update.sh`) adhering to project deployment standards. It pulls the latest branch commits, updates dependencies, runs database migrations, and restarts the systemd daemon:

```bash
chmod +x update.sh
./update.sh
```

**Workflow executed by `update.sh`:**
1. Navigates to `/home/dietpi/hahealth`.
2. Fetches remote git references (`git fetch --all --prune`).
3. Checks out the chosen or latest branch.
4. Pulls latest changes (`git pull origin <branch>`).
5. Updates Python packages (`./venv/bin/pip install -r requirements.txt`).
6. Executes database schema updates (`./venv/bin/python3 scripts/migrate_all.py`).
7. Restarts service (`sudo systemctl restart hahealth`).

---

## 6. Architecture & Subsystems

### Component Hierarchy

```
                               ┌─────────────────────────────────────────┐
                               │           Web Client / Browser          │
                               │  (Vanilla ES6 JS, CSS3, Material Icons) │
                               └────────────────────┬────────────────────┘
                                                    │ HTTP / REST / JWT
                                                    ▼
┌───────────────────────────┐           ┌─────────────────────────────────────────┐
│   Home Assistant Core     │◄─MQTT────►│              FastAPI ASGI               │
│ (Webhooks, To-Do, Sensors)│◄─HTTP────►│  (Routers: Auth, Users, Health, Admin) │
└───────────────────────────┘           └───────────┬─────────────────┬───────────┘
                                                    │                 │
                         SQLAlchemy ORM (SQLite3)   ▼                 ▼ External APIs
                                       ┌─────────────────┐       ┌───────────────────────┐
                                       │  health_app.db  │       │  Open Food Facts API  │
                                       │ (Users, Logs,   │       │  Google Gemini 2.5    │
                                       │  NutritionCache)│       └───────────────────────┘
                                       └─────────────────┘
```

### Data Storage & Migrations
- **Database Engine**: Local SQLite (`health_app.db`) accessed via SQLAlchemy session pools (`app/database.py`).
- **Connection Configuration**: Thread checks disabled (`check_same_thread=False`) to allow asynchronous request execution across threads.
- **Migration Pipeline**:
  - `database.init_db()` runs on application startup, creating missing tables and checking columns for nutrition cache, recipe ingredients, and meal windows.
  - `scripts/migrate_all.py` acts as the master migration script, incrementally applying `ALTER TABLE` operations while guarding against existing columns via `sqlite3.OperationalError` handling.

### Telemetry & Home Assistant Integration
- **MQTT Background Client** (`app/mqtt.py`): Managed inside FastAPI's async lifespan context.
- **Auto-Discovery**: On connection, publishes MQTT auto-discovery configuration topics to `<HASS_DISCOVERY_PREFIX>/sensor/hahealth/.../config`.
- **Inbound Subscriptions**: Subscribes to `<MQTT_TOPIC_PREFIX>/+` (e.g. `hahealth/log/blood_pressure`, `hahealth/log/weight`) to process external sensor data directly into the database.
- **Shopping List Synchronization**: Synchronizes grocery items bidirectionally with Home Assistant To-Do lists via REST (`/api/v1/shopping-list/items`) and the blueprint `blueprints/health_tracker_shopping_sync.yaml`, tagging items with `#healthtracker`.

### AI Health Insights (Google Gemini)
- **Engine**: Google GenAI SDK (`google-genai`) querying `gemini-2.5-flash`.
- **Pipeline**: Daily nutritional metrics (calories consumed, macro targets, exercises) and user pantry staples (`NutritionCache.is_staple = True`) are formatted into a structured prompt sent to Gemini via `POST /api/v1/nutrition/ask-gemini`.
- **Output**: Returns personalized, actionable advice focusing on macro balancing, micronutrient fulfillment, and pantry-friendly meal suggestions.

### Frontend Client & Theme Engine
- **Single Page Architecture**: Vanilla HTML5/CSS3 and JavaScript (`app/static/index.html`, `app/static/app.js`).
- **Hybrid Dashboard**: Circular SVG gauge for caloric intake alongside linear, color-coded macro bars:
  - 🔴 **Red**: Protein
  - 🟡 **Yellow**: Fat
  - 🔵 **Blue**: Carbohydrates
- **Token Handling**: Stores `access_token` and `refresh_token` in `localStorage`. Automatically intercepts 401 Unauthorized responses to transparently refresh expired tokens via an internal async queue (`refreshQueue`).
- **Safe Rendering**: All dynamic notifications utilize custom `showToast(message, type)` using `textContent` and direct DOM node creation, strictly eliminating `innerHTML` injection risks.
- **UI Debug Mode**: Admin toggle injects `.debug-mode` into `<body>`, outlining DOM cards and forms with their programmatic HTML IDs for rapid UI troubleshooting.

---

## 7. API Reference Link

Comprehensive endpoint specifications, schemas, query parameters, webhook formats, and error response envelopes are fully documented in the dedicated API specification:

👉 **[Complete API Reference Document (API.md)](./API.md)**

---

## 8. Troubleshooting & Diagnostics

The following matrix maps common runtime anomalies, system errors, and exit codes to immediate recovery actions:

| Issue / Symptom | Underlying Cause | Actionable Recovery Steps |
| :--- | :--- | :--- |
| **`Address already in use` (Port 8000)** | Another instance of Uvicorn or another service is listening on port 8000. | Locate and terminate the process: <br>`sudo lsof -i :8000`<br>`kill $(lsof -t -i :8000)` |
| **`sqlite3.OperationalError: no such table`** | Database schema was not initialized before starting application. | Execute database initialization and migration:<br>`python3 -c "from app.database import init_db; init_db()"`<br>`python3 scripts/migrate_all.py` |
| **`ModuleNotFoundError: No module named 'fastapi'`** | Python virtual environment is not activated or dependencies are missing. | Activate virtual environment and install requirements:<br>`source .venv/bin/activate`<br>`pip install -r requirements.txt` |
| **`401 Unauthorized: Could not validate credentials`** | Expired JWT token, invalid signature, or missing `Authorization: Bearer <token>` header. | Re-authenticate via `POST /auth/token` or trigger token refresh via `POST /auth/refresh`. For webhooks, verify `X-Webhook-Secret` matches an active API key. |
| **`MQTT connection refused` / No broker connection** | Broker address/port incorrect, broker down, or credentials missing. | Verify broker reachability: <br>`nc -zv $MQTT_BROKER $MQTT_PORT`<br>Check `.env` values for `MQTT_BROKER`, `MQTT_USERNAME`, and `MQTT_PASSWORD`. |
| **`Gemini API Error` / Nutrition advice fails** | Missing or invalid `GEMINI_API_KEY` environment variable. | Acquire an API key from Google AI Studio and append `GEMINI_API_KEY=AIzaSy...` to `.env`. Restart the server. |
| **`Duplicate medication log on same day`** | The application enforces a strict single-log rule per schedule window per calendar day. | Verify existing logs via `GET /api/v1/medications/log?date_str=YYYY-MM-DD`. If necessary, update the existing entry via `PUT` instead of creating a duplicate. |
| **`update.sh` fails with non-zero exit code** | Git local conflicts or permission errors executing `pip` / `systemctl`. | Run `git status` to resolve merge conflicts. Ensure current user has `sudo` privileges configured for `systemctl restart hahealth`. |
| **`404 Not Found` when adding to shopping list** | Item does not exist in local `nutrition_cache`. | Add food item to database first via `POST /api/v1/nutrition/` before adding to shopping list. |
