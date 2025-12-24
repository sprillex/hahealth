# Comprehensive Health Tracker

A robust, multi-user health tracking backend built with FastAPI, designed to integrate seamlessly with Home Assistant via webhooks or MQTT.

## Features

- **Multi-User Support**: Secure data segregation for multiple users.
- **Home Assistant Integration**: Two modes of integration:
    - **Webhooks**: For real-time logging of Blood Pressure, Medication, Exercise, and Food via `rest_command`.
    - **MQTT**: For auto-discovery of sensors (Weight, BP, Calories) and data ingestion via the MQTT bus.
- **Nutrition Tracking**: Open Food Facts API integration with local caching.
- **Medication Management**: Inventory tracking, refill alerts, and adherence logging.
- **Exercise Analysis**: Automatic calorie calculation using MET formulas if tracker data is missing.
- **Security**: JWT authentication for web clients and Shared Secret Keys for webhooks/MQTT.

## Prerequisites

- Python 3.9+
- pip (Python package manager)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/sprillex/hahealth](https://github.com/sprillex/hahealth)
    cd hahealth
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    # Linux/Mac
    source venv/bin/activate
    # Windows
    venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

You can configure the application using environment variables or a `.env` file (recommended).

1.  **Copy the example configuration:**
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    ```ini
    # MQTT Configuration (Optional, for Home Assistant Integration)
    MQTT_BROKER=192.168.1.50
    MQTT_USERNAME=homeassistant
    MQTT_PASSWORD=your_password
    ```

### Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MQTT_BROKER` | Hostname or IP of the MQTT broker (e.g., your HA IP) | `localhost` |
| `MQTT_PORT` | Port of the MQTT broker | `1883` |
| `MQTT_USERNAME` | Username for authentication (optional) | `None` |
| `MQTT_PASSWORD` | Password for authentication (optional) | `None` |
| `MQTT_TOPIC_PREFIX` | Prefix for subscription (subscribes to `prefix/#`) | `hahealth/log` |
| `HASS_DISCOVERY_PREFIX` | Prefix for Home Assistant discovery topics | `homeassistant` |

## Running the Application

1.  **Start the server:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The API will be available at `http://localhost:8000` (or `http://<your-ip>:8000` from other devices).

2.  **Access API Documentation:**
    Open your browser and navigate to `http://localhost:8000/docs` to see the interactive Swagger UI.

## Automatic Startup (Linux/systemd)

To ensure the application starts automatically on boot, you can create a systemd service.

1.  **Create a service file:**
    ```bash
    sudo nano /etc/systemd/system/hahealth.service
    ```

2.  **Paste the following configuration** (update paths and user as needed):
    ```ini
    [Unit]
    Description=Health Tracker API
    After=network.target

    [Service]
    User=<your_user>
    Group=<your_group>
    WorkingDirectory=/path/to/hahealth
    # Load configuration from .env file
    EnvironmentFile=/path/to/hahealth/.env
    # Or set variables directly here:
    # Environment="MQTT_BROKER=192.168.1.50"
    ExecStart=/path/to/hahealth/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Enable and start the service:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable hahealth
    sudo systemctl start hahealth
    ```

## Initial Setup & Administration (CLI)

Use the included CLI tool to manage users and API keys.

**Important:** Ensure your virtual environment is activated (`source venv/bin/activate`) before running these commands. Alternatively, use the full path to the python executable (e.g., `./venv/bin/python`).

1.  **Create the first user:**
    ```bash
    ./venv/bin/python -m app.cli create-user --name "johndoe" --password "securepass" --weight 75.0 --height 180.0
    ```
    *Note the `ID` returned in the output.*

2.  **Create an API Key for Home Assistant:**
    ```bash
    ./venv/bin/python -m app.cli create-apikey --user-id 1 --name "HomeAssistant"
    ```
    **IMPORTANT:** Copy the `SECRET KEY` displayed. You will not be able to see it again.

3.  **Reset a Password (if needed):**
    ```bash
    ./venv/bin/python -m app.cli reset-password --user-id 1 --password "newpassword"
    ```

4.  **Revoke an API Key:**
    ```bash
    ./venv/bin/python -m app.cli revoke-apikey --key-id 1
    ```

5.  **Make a User Admin:**
    ```bash
    ./venv/bin/python -m app.cli make-admin --user-id 1
    ```
    *Use `--revoke` flag to remove admin privileges.*

## Updating the Application

To update the application to the latest version:

1.  **Pull the latest changes:**
    ```bash
    cd hahealth
    git pull
    ```

2.  **Update dependencies:**
    ```bash
    ./venv/bin/pip install -r requirements.txt
    ```

3.  **Run Database Migrations:**
    If new features (like Imperial units, admin tables, etc.) were added, run the migration script:
    ```bash
    python3 scripts/migrate_all.py
    ```

4.  **Restart the service:**
    ```bash
    sudo systemctl restart hahealth
    ```

## Database Inspection

To view the raw data in the SQLite database, you can use the included inspection script.

1.  **List all tables and row counts:**
    ```bash
    python scripts/inspect_db.py
    ```

2.  **Dump a specific table:**
    ```bash
    python scripts/inspect_db.py users
    ```

3.  **Dump with limit (e.g., first 5 rows):**
    ```bash
    python scripts/inspect_db.py daily_logs --limit 5
    ```

4.  **Dump all tables:**
    ```bash
    python scripts/inspect_db.py --all
    ```

## Home Assistant Integration (Method 1: MQTT)

This is the recommended integration method. It supports automatic sensor discovery and data logging.

### How it Works
1.  **Shared Broker**: The app connects to the same MQTT broker as Home Assistant.
2.  **Auto Discovery**: The app publishes configuration messages to `homeassistant/sensor/...`.
3.  **Sensors**: Home Assistant automatically creates the following sensors for each user, prefixed with the user's name (e.g., "John Doe Weight"):
    - **Weight** (kg or lb)
    - **BP Systolic** (mmHg)
    - **BP Diastolic** (mmHg)
    - **Calories Consumed** (kcal)
    - **Calories Burned** (kcal)

    *These sensors update every 60 seconds.*

### Unified Logging (MQTT & Webhooks)

We provide a unified helper script (`HA_SCRIPTS.yaml`) that can log data via either MQTT or HTTP Webhooks. This simplifies your configuration by routing all logs through a single action.

#### 1. Setup

**A. Secrets (`secrets.yaml`):**
```yaml
hahealth_api_key: "YOUR_SECRET_KEY"
hahealth_webhook_url: "http://<YOUR_APP_IP>:8000/api/webhook/health"
```

**B. Script (`scripts.yaml`):**
Copy the content of `HA_SCRIPTS.yaml` into your `scripts.yaml`.

**C. REST Command (Required for API mode only):**
Add the content of `HA_REST_COMMAND.yaml` to your `configuration.yaml`.

#### 2. Usage Examples

**Option A: Log via MQTT (Default)**
```yaml
action: script.log_health_metric
data:
  method: "mqtt"
  topic_suffix: "vitals"
  data_type: "BLOOD_PRESSURE"
  metric_data:
    systolic: 120
    diastolic: 80
    pulse: 72
```

**Option B: Log via HTTP API**
```yaml
action: script.log_health_metric
data:
  method: "api"
  data_type: "MEDICATION_TAKEN"
  metric_data:
    med_name: "Aspirin"
    timestamp: "{{ now().isoformat() }}"
    med_window: "morning"
```

### Barcode Query Automation Example

You can set up an automation to scan a barcode via webhook, query the Health App for nutrition info, and display the result in a notification.

See [HA_AUTOMATION.yaml](HA_AUTOMATION.yaml) for the full configuration guide.

## Development

**Run Tests:**
```bash
# Ensure the current directory is in PYTHONPATH
export PYTHONPATH=$PYTHONPATH:.
pytest
```
