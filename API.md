# Comprehensive Health Tracker - API Reference

This document provides a comprehensive API specification for the Comprehensive Health Tracker application.

---

## 1. Overview

### Base URLs
- **Development/Local Server:** `http://localhost:8000`
- **Interactive Documentation (Swagger UI):** `http://localhost:8000/docs`
- **OpenAPI Schema:** `http://localhost:8000/openapi.json`

### Protocols & Content Types
- All API communication uses standard **HTTP/1.1** over HTTPS (or HTTP for local deployments).
- Default request and response format is **`application/json`**, except for authentication token endpoints which accept `application/x-www-form-urlencoded` or binary endpoints handling backup files.

### Versioning
- **`/auth/*`**: Authentication and token lifecycle endpoints.
- **`/api/v1/*`**: Core REST API endpoints (v1).
- **`/api/v2/*`**: Enhanced v2 interfaces (e.g. structured Nutrition v2 lookup and logging).
- **`/api/webhook/*`**: Integration endpoints for Home Assistant / Webhooks.

---

## 2. Authentication

The application supports multiple authentication mechanisms based on client context:

### 2.1 JWT Bearer Token Authentication
Used by web frontend clients and REST consumers for full user session access.

1. **Obtain Token Pair**: Call `POST /auth/token` with username and password in `application/x-www-form-urlencoded` body.
2. **Include in Header**: Attach the token in request headers:
   ```http
   Authorization: Bearer <access_token>
   ```
3. **Token Refresh**: When an access token expires, submit `POST /auth/refresh` with the `refresh_token` in the JSON body.

### 2.2 API Key / Webhook Secret
Used for persistent integrations (such as Home Assistant webhooks or automated scripts).

- **Header Authentication**:
  ```http
  X-Webhook-Secret: <api_key>
  ```
- **Query Parameter Authentication** (optional fallback for auto-login or webhooks):
  ```http
  GET /api/v1/users/me?api_key=<api_key>
  ```

---

## 3. Standard Envelopes & Error Formats

### 3.1 HTTP Status Codes
| Code | Meaning | Description |
| :--- | :--- | :--- |
| `200 OK` | Request Succeeded | Returned for successful reads, updates, and general commands. |
| `201 Created` | Resource Created | Returned upon successful creation of a resource. |
| `204 No Content` | Success (No Body) | Returned when a resource is successfully deleted. |
| `400 Bad Request` | Bad Request | Client specified invalid business parameters or missing required options. |
| `401 Unauthorized` | Unauthorized | Missing or invalid authentication credentials. |
| `403 Forbidden` | Forbidden | Insufficient permissions (e.g., admin required). |
| `404 Not Found` | Not Found | Requested entity or route does not exist. |
| `422 Unprocessable Entity` | Validation Error | Request body or parameter failed schema validation. |
| `500 Internal Server Error` | Internal Failure | Unexpected server issue. |

### 3.2 Error Schema (`HTTPValidationError` & Standard Error)
When FastAPI validation fails (HTTP 422), responses return:
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

Standard application errors (e.g., HTTP 400, 401, 404) return:
```json
{
  "detail": "Descriptive error message"
}
```

---

## 4. Endpoints by Resource

### 4.1 Authentication & Tokens

#### `POST /auth/token`
Obtains a JWT access token and refresh token using username and password.

- **Authentication**: None (Public)
- **Content-Type**: `application/x-www-form-urlencoded`
- **Request Body**:
  - `username` (string, required)
  - `password` (string, required)
- **Success Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "refresh_token": "eyJhbGciOiJIUzI1Ni...",
    "token_type": "bearer"
  }
  ```
- **Error Responses**: `401 Unauthorized` (Incorrect username or password), `422 Unprocessable Entity`.

---

#### `POST /auth/refresh`
Exchanges a valid refresh token for a new access token and refresh token pair.

- **Authentication**: None (Public)
- **Request Body**:
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1Ni..."
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "refresh_token": "eyJhbGciOiJIUzI1Ni...",
    "token_type": "bearer"
  }
  ```
- **Error Responses**: `401 Unauthorized` (Invalid or expired refresh token).

---

### 4.2 Users & API Keys

#### `POST /api/v1/users/`
Creates a new user profile.

- **Authentication**: None (Public)
- **Request Body**:
  ```json
  {
    "username": "johndoe",
    "password": "securepassword",
    "weight_kg": 75.0,
    "height_cm": 180.0,
    "unit_system": "METRIC",
    "birth_year": 1990,
    "date_of_birth": "1990-05-15",
    "gender": "M",
    "goal_weight_kg": 70.0,
    "calorie_goal": 2000,
    "timezone": "America/New_York",
    "theme_preference": "DARK"
  }
  ```
- **Success Response (200 OK)**: User profile object.
- **Error Responses**: `400 Bad Request` (Username already registered).

---

#### `GET /api/v1/users/me`
Retrieves the profile of the currently authenticated user.

- **Authentication**: Bearer Token or API Key
- **Success Response (200 OK)**:
  ```json
  {
    "id": 1,
    "username": "johndoe",
    "weight_kg": 75.0,
    "height_cm": 180.0,
    "unit_system": "METRIC",
    "birth_year": 1990,
    "date_of_birth": "1990-05-15",
    "gender": "M",
    "goal_weight_kg": 70.0,
    "calorie_goal": 2000,
    "timezone": "America/New_York",
    "theme_preference": "DARK",
    "is_admin": false,
    "window_morning_start": "06:00:00",
    "window_afternoon_start": "12:00:00",
    "window_evening_start": "17:00:00",
    "window_bedtime_start": "21:00:00"
  }
  ```

---

#### `PUT /api/v1/users/me`
Updates user profile settings and preferences.

- **Authentication**: Bearer Token or API Key
- **Request Body**: Partial or full `UserUpdate` schema fields (e.g. `weight_kg`, `calorie_goal`, `timezone`).
- **Success Response (200 OK)**: Updated user profile object.

---

#### `PUT /api/v1/users/me/password`
Updates the password for the current user.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "current_password": "oldpassword",
    "new_password": "newpassword123",
    "confirm_password": "newpassword123"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Password updated successfully"
  }
  ```

---

#### `GET /api/v1/users/me/keys`
Lists all active API keys created by the current user.

- **Authentication**: Bearer Token or API Key
- **Success Response (200 OK)**:
  ```json
  [
    {
      "id": 1,
      "name": "HomeAssistant Integration",
      "created_at": "2023-10-01T12:00:00",
      "last_used_at": "2023-10-02T15:30:00"
    }
  ]
  ```

---

#### `POST /api/v1/users/me/keys`
Generates a new API Key for integrations.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "name": "HomeAssistant Integration"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "id": 1,
    "name": "HomeAssistant Integration",
    "api_key": "sec_key_...",
    "created_at": "2023-10-01T12:00:00"
  }
  ```
  *(Note: `api_key` plaintext is only returned once upon creation)*.

---

#### `DELETE /api/v1/users/me/keys/{key_id}`
Revokes an API Key.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `key_id` (integer)
- **Success Response (200 OK)**: `{"message": "API Key revoked successfully"}`

---

### 4.3 Health Logging

#### `POST /api/v1/log/bp`
Logs a new blood pressure reading.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "systolic": 120,
    "diastolic": 80,
    "pulse": 72,
    "location": "Left Arm",
    "stress_level": 3,
    "meds_taken_before": "None",
    "timestamp": "2023-10-27T08:00:00Z"
  }
  ```
- **Success Response (200 OK)**: Blood pressure log object.

---

#### `GET /api/v1/log/history/bp`
Retrieves blood pressure history.

- **Authentication**: Bearer Token or API Key
- **Query Parameters**: `limit` (integer, default: 50)
- **Success Response (200 OK)**: Array of blood pressure log records.

---

#### `POST /api/v1/log/exercise`
Logs an exercise activity.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "activity_type": "Running",
    "duration_minutes": 30,
    "calories_burned": 300,
    "timestamp": "2023-10-27T18:00:00Z"
  }
  ```
- **Success Response (200 OK)**: `{"message": "Exercise logged", "calories_burned": 300}`

---

#### `GET /api/v1/log/history/exercise`
Retrieves exercise log history.

- **Authentication**: Bearer Token or API Key
- **Query Parameters**: `limit` (integer, default: 50)
- **Success Response (200 OK)**: Array of exercise log records.

---

#### `PUT /api/v1/log/exercise/{log_id}`
Updates an exercise log entry.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `log_id` (integer)
- **Request Body**:
  ```json
  {
    "activity_type": "Running",
    "duration_minutes": 45,
    "calories_burned": 450
  }
  ```
- **Success Response (200 OK)**: Updated exercise log object.

---

#### `DELETE /api/v1/log/exercise/{log_id}`
Deletes an exercise log entry.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `log_id` (integer)
- **Success Response (200 OK)**: `{"message": "Exercise log deleted"}`

---

#### `PUT /api/v1/log/food/{log_id}`
Updates a food log entry.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `log_id` (integer)
- **Request Body**:
  ```json
  {
    "quantity": 2.0,
    "serving_size": "1 apple",
    "meal_id": "Breakfast"
  }
  ```
- **Success Response (200 OK)**: Updated food log object.

---

#### `DELETE /api/v1/log/food/{log_id}`
Deletes a food log entry.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `log_id` (integer)
- **Success Response (200 OK)**: `{"message": "Food log deleted"}`

---

#### `GET /api/v1/log/summary`
Gets daily summary metrics for a given date.

- **Authentication**: Bearer Token or API Key
- **Query Parameters**: `date_str` (string, optional format `YYYY-MM-DD`, defaults to today in user's timezone)
- **Success Response (200 OK)**:
  ```json
  {
    "date": "2023-10-27",
    "user": { ... },
    "calories_consumed": 1850,
    "calorie_goal": 2000,
    "calories_burned": 300,
    "net_calories": 1550,
    "protein_g": 110,
    "fat_g": 60,
    "carbs_g": 210,
    "fiber_g": 25,
    "sodium_mg": 1800,
    "food_logs": [ ... ],
    "exercises": [ ... ],
    "bp_logs": [ ... ]
  }
  ```

---

#### `GET /api/v1/log/reports/compliance`
Generates a medication compliance report.

- **Authentication**: Bearer Token or API Key
- **Success Response (200 OK)**: Compliance metrics report.

---

#### `GET /api/v1/log/reports/adherence`
Generates a medication adherence report.

- **Authentication**: Bearer Token or API Key
- **Success Response (200 OK)**: Detailed adherence report.

---

### 4.4 Medications & Prescribers

#### `GET /api/v1/medications/`
Lists all medications for the user.

- **Authentication**: Bearer Token or API Key
- **Query Parameters**: `skip` (int, default: 0), `limit` (int, default: 100)
- **Success Response (200 OK)**: Array of Medication objects.

---

#### `POST /api/v1/medications/`
Creates a new medication entry.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "name": "Lisinopril",
    "dosage": "10mg",
    "form": "Pill",
    "inventory": 30,
    "refill_threshold": 5,
    "is_tracked": true,
    "sched_morning": true,
    "sched_afternoon": false,
    "sched_evening": false,
    "sched_bedtime": false,
    "prescriber_id": 1
  }
  ```
- **Success Response (200 OK)**: Created Medication object.

---

#### `PUT /api/v1/medications/{med_id}`
Updates medication details.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `med_id` (integer)
- **Request Body**: Partial/Full Medication payload.
- **Success Response (200 OK)**: Updated Medication object.

---

#### `POST /api/v1/medications/{med_id}/refill`
Refills inventory for a medication.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `med_id` (integer)
- **Request Body**:
  ```json
  {
    "quantity": 30
  }
  ```
- **Success Response (200 OK)**: Updated Medication object.

---

#### `GET /api/v1/medications/log`
Retrieves medication logs for a specified date.

- **Authentication**: Bearer Token or API Key
- **Query Parameters**: `date_str` (string YYYY-MM-DD, optional)
- **Success Response (200 OK)**: Array of medication log entries.

---

#### `PUT /api/v1/medications/log/{log_id}`
Updates a medication log entry.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `log_id` (integer)
- **Success Response (200 OK)**: Updated Medication log object.

---

#### `DELETE /api/v1/medications/log/{log_id}`
Deletes a medication log entry.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `log_id` (integer)
- **Success Response (200 OK)**: `{"message": "Medication log deleted"}`

---

#### `GET /api/v1/prescribers/`
Lists prescribers for the user.

- **Authentication**: Bearer Token or API Key
- **Query Parameters**: `skip` (int, default: 0), `limit` (int, default: 100)
- **Success Response (200 OK)**: Array of Prescriber objects.

---

#### `POST /api/v1/prescribers/`
Creates a new prescriber.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "name": "Dr. Sarah Smith",
    "specialty": "Cardiology",
    "phone": "555-0199",
    "email": "drsmith@example.com",
    "address": "100 Medical Plaza"
  }
  ```
- **Success Response (200 OK)**: Created Prescriber object.

---

### 4.5 Medical History

#### `GET /api/v1/medical/allergies`
Lists all recorded allergies.

- **Authentication**: Bearer Token or API Key
- **Success Response (200 OK)**: List of Allergy objects.

---

#### `POST /api/v1/medical/allergies`
Logs a new allergy.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "allergen": "Penicillin",
    "severity": "Severe",
    "reaction": "Hives and swelling",
    "notes": "Diagnosed in 2015"
  }
  ```
- **Success Response (200 OK)**: Created Allergy object.

---

#### `PUT /api/v1/medical/allergies/{allergy_id}`
Updates an allergy record.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `allergy_id` (integer)
- **Success Response (200 OK)**: Updated Allergy object.

---

#### `DELETE /api/v1/medical/allergies/{allergy_id}`
Deletes an allergy record.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `allergy_id` (integer)
- **Success Response (204 No Content)**: Empty response.

---

#### `GET /api/v1/medical/vaccinations`
Lists vaccination logs.

- **Authentication**: Bearer Token or API Key
- **Success Response (200 OK)**: List of Vaccination records.

---

#### `POST /api/v1/medical/vaccinations`
Logs a vaccination entry.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "vaccine_type": "Influenza",
    "date_administered": "2023-10-01",
    "expiration_date": "2024-10-01",
    "lot_number": "FL12345",
    "administered_by": "CVS Pharmacy",
    "notes": "Annual flu shot"
  }
  ```
- **Success Response (200 OK)**: Created Vaccination object.

---

#### `GET /api/v1/medical/reports/vaccinations`
Generates a structured vaccination status report.

- **Authentication**: Bearer Token or API Key
- **Success Response (200 OK)**: Report mapping vaccine categories to compliance status (e.g. Up to date, Overdue).

---

### 4.6 Nutrition (v1 & v2)

#### `POST /api/v1/nutrition/`
Creates a new custom item in the local nutrition database cache.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "food_name": "Greek Yogurt",
    "brand": "Chobani",
    "barcode": "073956000010",
    "calories": 130.0,
    "protein": 12.0,
    "fat": 2.5,
    "carbs": 15.0,
    "fiber": 0.0,
    "sodium": 55.0,
    "is_staple": true
  }
  ```
- **Success Response (200 OK)**: Created `NutritionCache` object.

---

#### `GET /api/v1/nutrition/list`
Lists cached nutrition items.

- **Authentication**: Bearer Token or API Key
- **Query Parameters**:
  - `skip` (int, default: 0)
  - `limit` (int, default: 50)
  - `search` (string, optional)
  - `include_hidden` (boolean, default: false)
  - `is_staple` (boolean, optional)
- **Success Response (200 OK)**: List of `NutritionCache` items.

---

#### `GET /api/v1/nutrition/search`
Searches food items in local cache and external sources (Open Food Facts).

- **Authentication**: Bearer Token or API Key
- **Query Parameters**:
  - `query` (string, required)
  - `scope` (string, default: `all`)
- **Success Response (200 OK)**: Array of matching food items.

---

#### `GET /api/v1/nutrition/{food_id}`
Retrieves details for a cached food item.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `food_id` (integer)
- **Success Response (200 OK)**: `NutritionCache` object.

---

#### `PUT /api/v1/nutrition/{food_id}`
Updates a cached food item.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `food_id` (integer)
- **Request Body**: `NutritionCacheUpdate` payload.
- **Success Response (200 OK)**: Updated `NutritionCache` object.

---

#### `DELETE /api/v1/nutrition/{food_id}`
Deletes a cached food item.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `food_id` (integer)
- **Success Response (200 OK)**: `{"message": "Item deleted"}`

---

#### `POST /api/v1/nutrition/log`
Logs a food item consumption to daily logs (v1 schema).

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "food_name": "Greek Yogurt",
    "barcode": "073956000010",
    "serving_size": "1 cup",
    "quantity": 1.0,
    "meal_id": "Breakfast",
    "timestamp": "2023-10-27T08:30:00Z"
  }
  ```
- **Success Response (200 OK)**: Created Food Log object.

---

#### `POST /api/v1/nutrition/ask-gemini`
Requests AI-driven nutrition advice from Google Gemini based on recent daily logs and staple foods.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "date_str": "2023-10-27"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "advice": "Based on your daily summary..."
  }
  ```

---

#### `GET /api/v2/nutrition/generate_upc`
Generates a unique local UPC barcode number for custom foods.

- **Authentication**: Bearer Token or API Key
- **Success Response (200 OK)**:
  ```json
  {
    "upc": "200000000123"
  }
  ```

---

#### `GET /api/v2/nutrition/lookup/{barcode}`
Looks up structured Nutrition v2 metadata by barcode.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `barcode` (string)
- **Success Response (200 OK)**:
  ```json
  {
    "barcode": "073956000010",
    "food_item": {
      "name": "Greek Yogurt",
      "brand": "Chobani"
    },
    "serving_info": {
      "serving_size_unit": "g",
      "serving_weight_grams": 170.0
    },
    "macros": {
      "calories": 130.0,
      "protein": 12.0,
      "fat": 2.5,
      "carbs": 15.0,
      "fiber": 0.0,
      "sodium": 55.0
    },
    "micros": {},
    "analysis": {},
    "metadata": {
      "is_staple": true,
      "on_shopping_list": false
    }
  }
  ```

---

#### `POST /api/v2/nutrition/log`
Logs a food item entry using the structured Nutrition v2 schema.

- **Authentication**: Bearer Token or API Key
- **Query Parameters**: `check_existence` (boolean, default: false)
- **Request Body**: `NutritionLogV2` schema payload.
- **Success Response (200 OK)**: Created Food Log object.

---

### 4.7 Recipes

#### `GET /api/v1/recipes/`
Lists all recipes created by the user.

- **Authentication**: Bearer Token or API Key
- **Success Response (200 OK)**: Array of Recipe objects (including ingredients).

---

#### `POST /api/v1/recipes/`
Creates a new recipe.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "name": "Chicken Salad",
    "servings": 2,
    "instructions": "Mix grilled chicken with greens and dressing.",
    "ingredients": [
      {
        "nutrition_cache_id": 5,
        "quantity": 200,
        "unit": "g"
      }
    ]
  }
  ```
- **Success Response (200 OK)**: Created Recipe object.

---

#### `GET /api/v1/recipes/{recipe_id}`
Gets details of a specific recipe.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `recipe_id` (integer)
- **Success Response (200 OK)**: Recipe object.

---

#### `PUT /api/v1/recipes/{recipe_id}`
Updates an existing recipe.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `recipe_id` (integer)
- **Request Body**: `RecipeUpdate` schema payload.
- **Success Response (200 OK)**: Updated Recipe object.

---

#### `DELETE /api/v1/recipes/{recipe_id}`
Deletes a recipe.

- **Authentication**: Bearer Token or API Key
- **Path Parameters**: `recipe_id` (integer)
- **Success Response (200 OK)**: `{"message": "Recipe deleted"}`

---

### 4.8 Shopping List

#### `POST /api/v1/shopping-list/items`
Adds a food item to the shopping list by name.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "food_name": "Greek Yogurt"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Item added to shopping list",
    "food_name": "Greek Yogurt"
  }
  ```
- **Error Responses**: `404 Not Found` (Item not found in nutrition cache).

---

#### `DELETE /api/v1/shopping-list/items`
Removes a food item from the shopping list by name.

- **Authentication**: Bearer Token or API Key
- **Request Body**:
  ```json
  {
    "food_name": "Greek Yogurt"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Item removed from shopping list",
    "food_name": "Greek Yogurt"
  }
  ```
- **Error Responses**: `404 Not Found` (Item not found in nutrition cache).

---

### 4.9 Webhook & Ingestion

#### `POST /api/webhook/health`
Ingests health metrics via HTTP webhook (used by Home Assistant or automation scripts).

- **Authentication**: `X-Webhook-Secret` header or `api_key` query parameter required.
- **Request Body**:
  ```json
  {
    "data_type": "BLOOD_PRESSURE",
    "payload": {
      "systolic": 120,
      "diastolic": 80,
      "pulse": 70
    }
  }
  ```
  *(Supported `data_type` values: `BLOOD_PRESSURE`, `MEDICATION_TAKEN`, `MEDICATION_WINDOW_TAKEN`, `EXERCISE_SESSION`, `FOOD_LOG`, `WEIGHT`)*.
- **Success Response (200 OK)**: `{"status": "success", "message": "Logged successfully"}`

---

#### `GET /api/webhook/nutrition/{barcode}`
Retrieves nutrition information formatted for Home Assistant notifications or voice feedback.

- **Authentication**: `X-Webhook-Secret` header or `api_key` query parameter required.
- **Path Parameters**: `barcode` (string)
- **Success Response (200 OK)**:
  ```json
  {
    "found": true,
    "food_name": "Greek Yogurt",
    "calories": 130,
    "protein": 12,
    "fat": 2.5,
    "carbs": 15
  }
  ```

---

### 4.10 Administration & System

#### `GET /api/v1/admin/mqtt_status`
Checks the current connection status and broker configuration of the MQTT client.

- **Authentication**: Bearer Token or API Key (Admin required)
- **Success Response (200 OK)**:
  ```json
  {
    "connected": true,
    "broker": "192.168.1.50",
    "port": 1883
  }
  ```

---

#### `POST /api/v1/admin/key`
Sets the database backup encryption key.

- **Authentication**: Bearer Token or API Key (Admin required)
- **Request Body**: `{"key": "mysecretkey"}`
- **Success Response (200 OK)**: `{"message": "Backup key set successfully"}`

---

#### `POST /api/v1/admin/backup`
Triggers an encrypted database backup generation.

- **Authentication**: Bearer Token or API Key (Admin required)
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Backup created successfully",
    "filename": "backup_20231027_120000.enc"
  }
  ```

---

#### `GET /api/v1/admin/backup/latest`
Downloads the latest generated database backup file.

- **Authentication**: Bearer Token or API Key (Admin required)
- **Success Response (200 OK)**: Binary file download (`application/octet-stream`).

---

#### `POST /api/v1/admin/restore`
Restores the SQLite database from an uploaded backup file.

- **Authentication**: Bearer Token or API Key (Admin required)
- **Content-Type**: `multipart/form-data`
- **Form File**: `file` (backup `.enc` or `.db` file)
- **Success Response (200 OK)**: `{"message": "Database restored successfully"}`

---

#### `GET /api/v1/version`
Retrieves application build version and compilation timestamp.

- **Authentication**: None (Public)
- **Success Response (200 OK)**:
  ```json
  {
    "version": "1.0.0",
    "date": "2023-10-27"
  }
  ```

---

#### `GET /`
Serves the web dashboard frontend (`app/static/index.html`).

- **Authentication**: None (Public)
- **Success Response (200 OK)**: HTML document.

---

## 5. Pagination & Querying Rules

- **Limit & Offset Pagination**: Endpoints returning collections (`GET /api/v1/medications/`, `GET /api/v1/prescribers/`, `GET /api/v1/nutrition/list`) use standard zero-indexed query parameters:
  - `skip` (integer, default: `0`): Number of records to skip.
  - `limit` (integer, default: `50` or `100`): Maximum number of records to return.
- **Search Filtering**:
  - `GET /api/v1/nutrition/list` supports case-insensitive string filtering via `search=<term>` and Boolean filtering via `is_staple=true|false`.
  - `GET /api/v1/nutrition/search` accepts `query=<term>` to query local database cache and Open Food Facts.
