# Comprehensive Health Tracker

A robust, multi-user health tracking backend and web dashboard built with FastAPI and SQLite. It provides centralized management for health vitals, nutrition, medications, recipes, medical records, and integrates seamlessly with Home Assistant via webhooks and MQTT.

## Features

- **Multi-User Health Tracking**: Individual user isolation with customizable profile metrics, daily calorie goals, timezones, and schedule windows.
- **Vitals & Exercise Logging**: Track blood pressure readings, heart rate, weight, and physical activity with automatic calorie expenditure calculations.
- **Nutrition & Recipe Management**: Search Open Food Facts and local caches, calculate macronutrient/micronutrient breakdowns, manage staple foods, and build custom recipes.
- **Medication & Adherence Tracking**: Schedule morning/afternoon/evening/bedtime dosages, track pill inventory with refill thresholds, log adherence, and manage prescribers.
- **Medical Records**: Log vaccinations and allergies, with automated compliance and status report generation.
- **AI Health Insights**: Google Gemini integration for personalized nutrition advice based on daily summaries and staple foods.
- **Home Assistant & Webhook Integration**: Auto-discovery MQTT sensors, bidirectional shopping list sync, and webhook payloads for automated logging.
- **Admin & Security**: Role-based administration, persistent API key management, JWT auth with auto-refresh, and encrypted database backup/restore features.

## Tech Stack & Architecture

- **Backend Framework**: Python 3.9+ / FastAPI (Asynchronous ASGI application)
- **Database Layer**: SQLite3 with SQLAlchemy ORM and lightweight manual migration runner (`scripts/migrate_all.py`)
- **Authentication**: JWT Bearer Tokens (`python-jose`, `passlib`, `bcrypt`) and API Key / Webhook secrets
- **Messaging & Integration**: Paho-MQTT client for Home Assistant discovery and real-time state telemetry
- **External AI & Data Services**: `google-genai` (Gemini 2.5 Flash) for nutrition insights, Open Food Facts API for food item caching
- **Frontend Web Interface**: Vanilla HTML5, CSS3, JavaScript ES6 (`app/static/index.html` & `app/static/app.js`) with responsive dark/light theme support
- **ASGI Server**: Uvicorn

## Repository Layout

```
.
├── app/                      # Application core package
│   ├── main.py               # FastAPI entry point & application setup
│   ├── models.py             # SQLAlchemy database models
│   ├── schemas.py            # Pydantic data schemas (v1 & v2)
│   ├── schemas_shopping.py   # Shopping list schemas
│   ├── auth.py               # Security, password hashing, & JWT mechanics
│   ├── database.py           # Database connection & session setup
│   ├── mqtt.py               # MQTT client & Home Assistant sensor discovery
│   ├── cli.py                # Command line management interface
│   ├── routers/              # Endpoint route handlers
│   └── static/               # Frontend web client assets (index.html, app.js)
├── blueprints/               # Home Assistant blueprint YAMLs
├── scripts/                  # Utility scripts (migrate_all.py, inspect_db.py)
├── tests/                    # Pytest unit and integration test suite
├── verification/             # UI and feature verification scripts (Playwright)
├── API.md                    # Detailed API specification & endpoint reference
├── HA_AUTOMATION.yaml        # Example Home Assistant automation templates
├── HA_REST_COMMAND.yaml      # REST command definitions for Home Assistant
├── HA_SCRIPTS.yaml           # Unified logging scripts for Home Assistant
├── requirements.txt          # Python project dependencies
├── update.sh                 # Master application update script
└── WIKI.md                   # Home Assistant integration guide
```

## Prerequisites & Setup

### Prerequisites
- Python 3.9 or higher
- `pip` package manager
- `git`

### Step-by-Step Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sprillex/hahealth.git
   cd hahealth
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database schema:**
   ```bash
   python3 scripts/migrate_all.py
   ```

## Configuration

Configure the application using environment variables or a `.env` file in the project root:

1. **Copy the example configuration file:**
   ```bash
   cp .env.example .env
   ```

2. **Configure configuration parameters:**

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `MQTT_BROKER` | Hostname or IP address of the MQTT broker | `localhost` |
| `MQTT_PORT` | Port for the MQTT broker connection | `1883` |
| `MQTT_USERNAME` | Username for MQTT authentication (optional) | `None` |
| `MQTT_PASSWORD` | Password for MQTT authentication (optional) | `None` |
| `MQTT_TOPIC_PREFIX` | MQTT topic prefix for inbound log subscriptions | `hahealth/log` |
| `HASS_DISCOVERY_PREFIX` | Home Assistant MQTT auto-discovery prefix | `homeassistant` |
| `GEMINI_API_KEY` | API Key for Google Gemini AI nutrition insights | `None` |

## Running the Application

### Development Mode
Run the server with auto-reload enabled:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Mode
Run the ASGI server without reload:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Automatic Startup (systemd)
To run the server as a background service on Linux:

1. **Create service file** at `/etc/systemd/system/hahealth.service`:
   ```ini
   [Unit]
   Description=Comprehensive Health Tracker API
   After=network.target

   [Service]
   User=dietpi
   WorkingDirectory=/home/dietpi/hahealth
   EnvironmentFile=/home/dietpi/hahealth/.env
   ExecStart=/home/dietpi/hahealth/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and start the service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable hahealth
   sudo systemctl start hahealth
   ```

## Initial Setup & Administration (CLI)

Use the CLI interface to create users, generate persistent API keys, or assign administrative rights.

1. **Create First User:**
   ```bash
   PYTHONPATH=. ./venv/bin/python -m app.cli create-user --name "johndoe" --password "securepassword" --weight 75.0 --height 180.0
   ```

2. **Promote User to Admin:**
   ```bash
   PYTHONPATH=. ./venv/bin/python -m app.cli make-admin --user-id 1
   ```

3. **Generate API Key for Home Assistant:**
   ```bash
   PYTHONPATH=. ./venv/bin/python -m app.cli create-apikey --user-id 1 --name "HomeAssistant"
   ```

4. **Reset User Password:**
   ```bash
   PYTHONPATH=. ./venv/bin/python -m app.cli reset-password --user-id 1 --password "newpassword"
   ```

## Testing & Verification

### Running Unit & Integration Tests
Execute the Pytest test suite:
```bash
PYTHONPATH=. pytest
```

### Playwright UI Verification
Run interactive frontend verification scripts:
```bash
PYTHONPATH=. python3 verification/verify_ui.py
```

## API Reference

The application exposes a RESTful interface covering user management, vitals logging, medication adherence, nutrition, recipes, and webhook ingestion.

For complete endpoint documentation, request schemas, parameters, response envelopes, and code examples, consult the dedicated reference document:

📖 **[API.md - Complete API Reference Document](./API.md)**
