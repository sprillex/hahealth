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

## Development

**Run Tests:**
```bash
# Ensure the current directory is in PYTHONPATH
export PYTHONPATH=$PYTHONPATH:.
pytest
```
