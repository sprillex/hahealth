# Health Tracker Shopping List Sync Blueprint

This directory contains a Home Assistant Blueprint (`health_tracker_shopping_sync.yaml`) that synchronizes your Health Tracker shopping list with a Home Assistant To-Do list.

## Features
*   **Two-way Sync:** Adding/Removing items in Health Tracker updates Home Assistant. Adding/Removing items in Home Assistant updates Health Tracker.
*   **Tagging:** Items added by Health Tracker are tagged with `#healthtracker` in the description.
*   **Manual Items:** Items added manually to Home Assistant (without the tag) are ignored if they don't exist in the Health Tracker database.

## Prerequisites

### 1. Secrets Configuration (`secrets.yaml`)
Add your Health Tracker API Key to your `secrets.yaml` file.

```yaml
# secrets.yaml
health_tracker_api_key: "YOUR_API_KEY_HERE"
# Optional: Store your full base URL if desired, though REST commands often use hardcoded URLs or specific secrets
health_tracker_base_url: "http://<YOUR_SERVER_IP>:8000"
```

### 2. REST Command Configuration (`configuration.yaml`)
Add the following `rest_command` definitions to your `configuration.yaml` file. These are used by the Blueprint to communicate with the Health Tracker.

Replace `http://<YOUR_SERVER_IP>:8000` with the actual IP address and port of your Health Tracker instance.

```yaml
# configuration.yaml
rest_command:
  health_tracker_add:
    url: "http://<YOUR_SERVER_IP>:8000/api/v1/shopping-list/items"
    method: POST
    headers:
      X-API-Key: "!secret health_tracker_api_key"
      Content-Type: "application/json"
    payload: '{"name": "{{ name }}"}'

  health_tracker_remove:
    url: "http://<YOUR_SERVER_IP>:8000/api/v1/shopping-list/items"
    method: DELETE
    headers:
      X-API-Key: "!secret health_tracker_api_key"
      Content-Type: "application/json"
    payload: '{"name": "{{ name }}"}'
```

### 3. Setup Automation
1.  Copy the `health_tracker_shopping_sync.yaml` file to your Home Assistant `blueprints/automation/` directory (or import it if hosted online).
2.  Go to **Settings > Automations & Scenes > Blueprints**.
3.  Locate "Health Tracker Shopping List Sync" and click **Create Automation**.
4.  Fill in the inputs:
    *   **To-Do List:** Select your Home Assistant Shopping List (e.g., `todo.shopping_list`).
    *   **Health Tracker Sensor:** Select the MQTT sensor (e.g., `sensor.your_name_shopping_list`).
    *   **Add Item Service:** `rest_command.health_tracker_add` (ensure this matches your `configuration.yaml` setup).
    *   **Remove Item Service:** `rest_command.health_tracker_remove`.
5.  Save the automation.

## How it Works
*   **Tracker -> HA:** When the Health Tracker MQTT sensor updates, the automation checks the To-Do list.
    *   New items are added with `#healthtracker` in the description.
    *   Items removed from the Tracker (and possessing the tag) are removed from HA.
    *   Items in HA without the tag are ignored (preserved).
*   **HA -> Tracker:**
    *   When the To-Do list changes, the automation compares it with the Tracker state.
    *   New items (untagged) are sent to the Tracker via the `add` REST command.
    *   Items missing from HA (that exist in the Tracker) are removed from the Tracker via the `remove` REST command.
