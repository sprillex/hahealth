# Comprehensive Health Tracker

A robust, multi-user health tracking backend built with FastAPI, designed to integrate seamlessly with Home Assistant via webhooks.

## Features

- **Multi-User Support**: Secure data segregation for multiple users.
- **Home Assistant Integration**: Webhooks for real-time logging of Blood Pressure, Medication, Exercise, and Food.
- **Nutrition Tracking**: Open Food Facts API integration with local caching.
- **Medication Management**: Inventory tracking, refill alerts, and adherence logging.
- **Exercise Analysis**: Automatic calorie calculation using MET formulas if tracker data is missing.
- **Security**: JWT authentication for web clients and Shared Secret Keys for webhooks.

## Prerequisites

- Python 3.9+
- pip (Python package manager)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/sprillex/hahealth
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

## Home Assistant Integration

To send data from Home Assistant to this application, use the `rest_command` integration or automation webhooks.

### Webhook Endpoint
`POST /api/webhook/health`

**Headers:**
- `Content-Type`: `application/json`
- `X-Webhook-Secret`: `<YOUR_GENERATED_SECRET_KEY>`

### Configuration Example (`configuration.yaml`)

Add these blocks to your Home Assistant `configuration.yaml` file to easily call the API from automations or scripts.

**Note:** Replace `!secret hahealth_api_key` with your actual API key or define it in your `secrets.yaml`.

```yaml
rest_command:
  # Log Blood Pressure
  # Expects variables: systolic, diastolic, pulse, stress_level (optional)
  log_blood_pressure:
    url: "http://<YOUR_APP_IP>:8000/api/webhook/health"
    method: POST
    headers:
      Content-Type: "application/json"
      X-Webhook-Secret: !secret hahealth_api_key
    payload: >
      {
        "data_type": "BLOOD_PRESSURE",
        "payload": {
          "systolic": {{ states('input_number.systolic') | int }},
          "diastolic": {{ states('input_number.diastolic') | int }},
          "pulse": {{ states('input_number.pulse') | int }},
          "location": "{{ states('input_select.bplocation') }}",
          "stress_level": {{ states('input_number.stress_level') | int }},
          "meds_taken_before": "NO"
        }
      }

  # Log Medication Taken
  # Expects variable: med_name
  # Optional: med_window (e.g. "morning", "evening")
  log_medication:
    url: "http://<YOUR_APP_IP>:8000/api/webhook/health"
    method: POST
    headers:
      Content-Type: "application/json"
      X-Webhook-Secret: !secret hahealth_api_key
    payload: >
      {
        "data_type": "MEDICATION_TAKEN",
        "payload": {
          "med_name": "{{ med_name }}",
          "timestamp": "{{ now().isoformat() }}",
          "med_window": "{{ med_window | default('evening') }}"
        }
      }

  # Log Exercise
  # Expects variables: activity, duration, calories
  log_exercise:
    url: "http://<YOUR_APP_IP>:8000/api/webhook/health"
    method: POST
    headers:
      Content-Type: "application/json"
      X-Webhook-Secret: !secret hahealth_api_key
    payload: >
      {
        "data_type": "EXERCISE_SESSION",
        "payload": {
          "activity_type": "{{ activity }}",
          "duration_minutes": {{ duration | int }},
          "calories_burned": {{ calories | int }}
        }
      }

  # Log Food (via Barcode)
  # Expects variables: barcode, meal, serving, quantity
  log_food:
    url: "http://<YOUR_APP_IP>:8000/api/webhook/health"
    method: POST
    headers:
      Content-Type: "application/json"
      X-Webhook-Secret: !secret hahealth_api_key
    payload: >
      {
        "data_type": "FOOD_LOG",
        "payload": {
          "barcode": "{{ barcode }}",
          "meal_id": "{{ meal }}",
          "serving_size": {{ serving | default(1) }},
          "quantity": {{ quantity | default(1) }}
        }
      }
```

## MQTT Integration

The application supports receiving health data via MQTT, useful for integration with Home Assistant's `mqtt.publish` service.

### Configuration

You can configure the MQTT connection by creating a `.env` file in the project root (recommended) or setting environment variables.

1.  **Copy the example configuration:**
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    ```ini
    MQTT_BROKER=192.168.1.50
    MQTT_USERNAME=homeassistant
    MQTT_PASSWORD=your_password
    ```

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MQTT_BROKER` | Hostname or IP of the MQTT broker (e.g., your HA IP) | `localhost` |
| `MQTT_PORT` | Port of the MQTT broker | `1883` |
| `MQTT_USERNAME` | Username for authentication (optional) | `None` |
| `MQTT_PASSWORD` | Password for authentication (optional) | `None` |
| `MQTT_TOPIC_PREFIX` | Prefix for subscription (subscribes to `prefix/#`) | `hahealth/log` |
| `HASS_DISCOVERY_PREFIX` | Prefix for Home Assistant discovery topics | `homeassistant` |

### How it Works with Home Assistant

1.  **Shared Broker**: This application connects to the **same** MQTT Broker that Home Assistant uses. You do not need to configure a new broker; just point this app to your existing one (often the "Mosquitto broker" Add-on in Home Assistant).
2.  **Auto Discovery**: Once connected, this app publishes "Discovery" messages to `homeassistant/sensor/...`. Home Assistant listens for these messages automatically.
3.  **No Manual Setup**: You do **not** need to manually configure sensors in your `configuration.yaml`. If the MQTT integration is enabled in Home Assistant, the sensors (Weight, Blood Pressure, etc.) will appear automatically under "Integrations" -> "MQTT".

### Home Assistant Auto Discovery

When MQTT is configured, the application automatically publishes discovery payloads to Home Assistant. This means sensors for your health data will appear automatically in Home Assistant without manual configuration.

**Sensors Created (per user):**
- **Weight**: Displays current weight (supports Metric/Imperial based on user profile).
- **Blood Pressure**: Two sensors for Systolic and Diastolic values.
- **Daily Calories**: Two sensors for 'Consumed' and 'Burned' calories for the current day.

The application updates these sensors every 60 seconds.

### Ingestion Payload Format

Send a JSON payload to `hahealth/log/any_subtopic`. The payload must include your API Key (`api_key`) and the `data_type`.

**Example: Log Blood Pressure**
```json
{
  "api_key": "YOUR_SECRET_API_KEY",
  "data_type": "BLOOD_PRESSURE",
  "payload": {
    "systolic": 120,
    "diastolic": 80,
    "pulse": 72,
    "location": "Left Arm",
    "stress_level": 5
  }
}
```

**Example: Home Assistant Script**

```yaml
alias: Log BP via MQTT
sequence:
  - service: mqtt.publish
    data:
      topic: hahealth/log/bp
      payload: >
        {
          "api_key": "!secret hahealth_api_key",
          "data_type": "BLOOD_PRESSURE",
          "payload": {
            "systolic": {{ states('input_number.systolic') | int }},
            "diastolic": {{ states('input_number.diastolic') | int }},
            "pulse": {{ states('input_number.pulse') | int }}
          }
        }
```

## Development

**Run Tests:**
```bash
# Ensure the current directory is in PYTHONPATH
export PYTHONPATH=$PYTHONPATH:.
pytest
```
