# Comprehensive Health Tracker API Documentation

This wiki documents the API endpoints available in the Comprehensive Health Tracker application.

## Table of Contents
1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Health Logging](#health-logging)
4. [Medications](#medications)
5. [Prescribers](#prescribers)
6. [Medical History](#medical-history)
7. [Nutrition](#nutrition)
8. [Admin Endpoints](#admin-endpoints)
9. [Webhook & MQTT Integration](#webhook--mqtt-integration)

---

## Authentication
Most endpoints require a Bearer Token (JWT) in the `Authorization` header, or an API Key in the `X-Webhook-Secret` header for specific endpoints.

### Login
*   **POST** `/auth/token`
    *   **Description:** Obtains a JWT access token for authentication.
    *   **Parameters:** `username` (string), `password` (string) - Send as `application/x-www-form-urlencoded`.
    *   **Response:** `{"access_token": "...", "token_type": "bearer"}`

---

## User Management

### Get Current User
*   **GET** `/api/v1/users/me`
    *   **Description:** Returns the profile of the currently logged-in user.
    *   **Response:** User Profile JSON.

### Update User Profile
*   **PUT** `/api/v1/users/me`
    *   **Description:** Updates the user's profile information.
    *   **Payload:**
        ```json
        {
          "weight_kg": 75.0,
          "height_cm": 180.0,
          "unit_system": "METRIC",
          "birth_year": 1990,
          "date_of_birth": "1990-01-01",
          "gender": "M",
          "goal_weight_kg": 70.0,
          "calorie_goal": 2000,
          "timezone": "America/New_York",
          "theme_preference": "DARK",
          "window_morning_start": "06:00:00",
          "window_afternoon_start": "12:00:00",
          "window_evening_start": "17:00:00",
          "window_bedtime_start": "21:00:00"
        }
        ```
    *   **Response:** Updated User Profile JSON.

### Change Password
*   **PUT** `/api/v1/users/me/password`
    *   **Description:** Changes the user's password.
    *   **Payload:**
        ```json
        {
          "current_password": "oldpassword",
          "new_password": "newpassword",
          "confirm_password": "newpassword"
        }
        ```
    *   **Response:** `{"message": "Password updated successfully"}`

---

## Health Logging

### Log Blood Pressure
*   **POST** `/api/v1/log/bp`
    *   **Description:** Logs a blood pressure reading.
    *   **Payload:**
        ```json
        {
          "systolic": 120,
          "diastolic": 80,
          "pulse": 70,
          "location": "Left Arm",
          "stress_level": 5,
          "meds_taken_before": "None"
        }
        ```
    *   **Response:** Created Blood Pressure Log JSON.

### Log Exercise
*   **POST** `/api/v1/log/exercise`
    *   **Description:** Logs an exercise session.
    *   **Payload:**
        ```json
        {
          "activity_type": "Running",
          "duration_minutes": 30,
          "calories_burned": 300
        }
        ```
    *   **Response:** `{"message": "Exercise logged", "calories_burned": 300}`

### Get Blood Pressure History
*   **GET** `/api/v1/log/history/bp`
    *   **Description:** Retrieves the last 50 blood pressure records.
    *   **Parameters:** `limit` (default: 50)
    *   **Response:** List of Blood Pressure records.

### Get Exercise History
*   **GET** `/api/v1/log/history/exercise`
    *   **Description:** Retrieves the last 50 exercise records.
    *   **Parameters:** `limit` (default: 50)
    *   **Response:** List of Exercise records.

### Get Daily Summary
*   **GET** `/api/v1/log/summary`
    *   **Description:** Retrieves health summary for a specific date (defaults to today).
    *   **Parameters:** `date_str` (YYYY-MM-DD, optional)
    *   **Response:** Summary of BP, Calories, Macros, Food Logs, and Exercises.

### Compliance Report
*   **GET** `/api/v1/log/reports/compliance`
    *   **Description:** Generates a medication compliance report.
    *   **Response:** JSON containing compliance percentages and missed/taken doses.

### Manage Exercise Log
*   **DELETE** `/api/v1/log/exercise/{log_id}`
    *   **Description:** Deletes a specific exercise log.
*   **PUT** `/api/v1/log/exercise/{log_id}`
    *   **Description:** Updates a specific exercise log.

### Manage Food Log
*   **DELETE** `/api/v1/log/food/{log_id}`
    *   **Description:** Deletes a specific food log.
*   **PUT** `/api/v1/log/food/{log_id}`
    *   **Description:** Updates a specific food log.

---

## Medications

### Create Medication
*   **POST** `/api/v1/medications/`
    *   **Description:** Adds a new medication.
    *   **Payload:** Medication details (name, frequency, inventory, schedules, etc.)
    *   **Response:** Created Medication JSON.

### Get Medications
*   **GET** `/api/v1/medications/`
    *   **Description:** Lists all medications for the user.
    *   **Response:** List of Medications.

### Update Medication
*   **PUT** `/api/v1/medications/{med_id}`
    *   **Description:** Updates an existing medication.
    *   **Payload:** Medication details to update.
    *   **Response:** Updated Medication JSON.

### Get Medication Logs
*   **GET** `/api/v1/medications/log`
    *   **Description:** Retrieves medication logs for a specific date.
    *   **Parameters:** `date_str` (YYYY-MM-DD, optional)
    *   **Response:** List of medication logs.

### Refill Medication
*   **POST** `/api/v1/medications/{med_id}/refill`
    *   **Description:** Adds inventory to a medication.
    *   **Payload:** `{"quantity": 30}`
    *   **Response:** Updated Medication JSON.

---

## Prescribers

### Create Prescriber
*   **POST** `/api/v1/prescribers/`
    *   **Description:** Adds a new prescriber.
    *   **Payload:**
        ```json
        {
          "name": "Dr. Smith",
          "specialty": "Cardiology",
          "phone": "555-0123",
          "email": "drsmith@example.com",
          "address": "123 Medical Way"
        }
        ```
    *   **Response:** Created Prescriber JSON.

### Get Prescribers
*   **GET** `/api/v1/prescribers/`
    *   **Description:** Lists all prescribers for the user.
    *   **Response:** List of Prescribers.

---

## Medical History

### Allergies
*   **POST** `/api/v1/medical/allergies`
    *   **Description:** Logs a new allergy.
*   **GET** `/api/v1/medical/allergies`
    *   **Description:** Lists all allergies.
*   **PUT** `/api/v1/medical/allergies/{id}`
    *   **Description:** Updates an allergy.
*   **DELETE** `/api/v1/medical/allergies/{id}`
    *   **Description:** Deletes an allergy.

### Vaccinations
*   **POST** `/api/v1/medical/vaccinations`
    *   **Description:** Logs a vaccination.
    *   **Payload:**
        ```json
        {
          "vaccine_type": "Influenza",
          "date_administered": "2023-10-01"
        }
        ```
*   **GET** `/api/v1/medical/vaccinations`
    *   **Description:** Lists vaccination history.
*   **GET** `/api/v1/medical/reports/vaccinations`
    *   **Description:** Generates a vaccination report including status (e.g., Overdue, Up to Date) for key vaccines like Influenza and Tdap.

---

## Nutrition

### Create Custom Food
*   **POST** `/api/v1/nutrition/`
    *   **Description:** Creates a manual nutrition entry (cache).
    *   **Payload:**
        ```json
        {
          "food_name": "My Meal",
          "calories": 500,
          "protein": 20,
          "fat": 15,
          "carbs": 60,
          "fiber": 5,
          "barcode": "optional"
        }
        ```

### Search Food
*   **GET** `/api/v1/nutrition/search`
    *   **Description:** Searches local nutrition cache.
    *   **Parameters:** `query` (string)

### Log Food Entry
*   **POST** `/api/v1/nutrition/log`
    *   **Description:** Logs a food item to the daily log.
    *   **Payload:**
        ```json
        {
          "food_name": "Apple",
          "barcode": "optional",
          "serving_size": 1.0,
          "quantity": 1.0,
          "meal_id": "Breakfast"
        }
        ```

---

## Admin Endpoints

### MQTT Status
*   **GET** `/api/v1/admin/mqtt_status`
    *   **Description:** Checks MQTT connection status and configuration.

### Backups
*   **POST** `/api/v1/admin/key`
    *   **Description:** Set the encryption key for backups.
*   **POST** `/api/v1/admin/backup`
    *   **Description:** Create a new encrypted backup of the database.
*   **GET** `/api/v1/admin/backup/latest`
    *   **Description:** Download the latest backup file.
*   **POST** `/api/v1/admin/restore`
    *   **Description:** Restore the database from an uploaded backup file.
    *   **Note:** Server logic may require a restart after restoration.

---

## Webhook & MQTT Integration

The application supports data ingestion via Webhooks (HTTP POST) and MQTT.

### Webhook Endpoint
*   **POST** `/api/webhook/health`
    *   **Headers:** `X-Webhook-Secret: <your_api_key>`
    *   **Payload:**
        ```json
        {
          "data_type": "BLOOD_PRESSURE",
          "payload": { ... }
        }
        ```

### Unified Logging (MQTT & Webhooks)

We recommend using the provided `log_health_metric` script (see `HA_SCRIPTS.yaml`) to securely log data from Home Assistant. This script supports both MQTT and HTTP API transports.

**Prerequisites:**
1.  Add the required keys (`hahealth_api_key`, `hahealth_webhook_url`, `hahealth_barcode_resource_url`) to your `secrets.yaml` (see README for details).
2.  Add the `log_health_metric` script from `HA_SCRIPTS.yaml` to your `scripts.yaml`.
3.  **CRITICAL:** Add the generic REST command from `HA_REST_COMMAND.yaml` to your `configuration.yaml`. This is required for the script to function correctly.

**Example Usage (MQTT):**
```yaml
action: script.log_health_metric
data:
  method: "mqtt"
  topic_suffix: "vitals"
  data_type: "BLOOD_PRESSURE"
  metric_data:
    systolic: 120
    diastolic: 80
    pulse: 70
```

**Example Usage (API):**
```yaml
action: script.log_health_metric
data:
  method: "api"
  data_type: "BLOOD_PRESSURE"
  metric_data:
    systolic: 120
    diastolic: 80
    pulse: 70
```

### Supported Data Types & Payloads
The following structures should be passed in the `metric_data` field of the script (or the `payload` field of the raw JSON).

#### 1. Blood Pressure
*   **data_type:** `BLOOD_PRESSURE`
*   **metric_data:**
    ```json
    {
      "systolic": 120,
      "diastolic": 80,
      "pulse": 70,
      "location": "Arm",
      "stress_level": 5,
      "meds_taken_before": "None"
    }
    ```

#### 2. Medication Taken
*   **data_type:** `MEDICATION_TAKEN`
*   **metric_data:**
    ```json
    {
      "med_name": "Aspirin",
      "timestamp": "2023-10-27T08:00:00Z",
      "med_window": "morning"
    }
    ```

#### 3. Exercise Session
*   **data_type:** `EXERCISE_SESSION`
*   **metric_data:**
    ```json
    {
      "activity_type": "Running",
      "duration_minutes": 30,
      "calories_burned": 300
    }
    ```

#### 4. Food Log
*   **data_type:** `FOOD_LOG`
*   **metric_data:**
    ```json
    {
      "food_name": "Banana",
      "serving_size": 1,
      "quantity": 1,
      "meal_id": "Snack"
    }
    ```

#### 5. Weight (New)
*   **data_type:** `WEIGHT`
*   **metric_data:**
    ```json
    {
      "weight": 75.5,
      "unit": "kg"
    }
    ```
    *   `unit` can be "kg" (default) or "lbs"/"pound"/"pounds".
