# Comprehensive Health Tracker - Technical API Reference

This document provides the complete API specification and operational reference for the Comprehensive Health Tracker (`hahealth`). It covers REST interfaces (v1 & v2), Home Assistant webhook protocols, authentication lifecycles, and the administrative CLI interface.

---

## Table of Contents
1. [Overview & Protocols](#1-overview--protocols)
2. [Authentication & Security](#2-authentication--security)
3. [Error Envelopes & Response Codes](#3-error-envelopes--response-codes)
4. [REST API Endpoint Reference](#4-rest-api-endpoint-reference)
   - [4.1 Authentication & Token Lifecycle (`/auth`)](#41-authentication--token-lifecycle-auth)
   - [4.2 User Management & Personal API Keys (`/api/v1/users`)](#42-user-management--personal-api-keys-apiv1users)
   - [4.3 Health & Activity Logging (`/api/v1/log`)](#43-health--activity-logging-apiv1log)
   - [4.4 Medications & Prescribers (`/api/v1/medications`, `/api/v1/prescribers`)](#44-medications--prescribers-apiv1medications-apiv1prescribers)
   - [4.5 Medical History (`/api/v1/medical`)](#45-medical-history-apiv1medical)
   - [4.6 Nutrition Services v1 & v2 (`/api/v1/nutrition`, `/api/v2/nutrition`)](#46-nutrition-services-v1--v2-apiv1nutrition-apiv2nutrition)
   - [4.7 Recipes Management (`/api/v1/recipes`)](#47-recipes-management-apiv1recipes)
   - [4.8 Shopping List Synchronization (`/api/v1/shopping-list`)](#48-shopping-list-synchronization-apiv1shopping-list)
   - [4.9 Webhook & Home Assistant Ingestion (`/api/webhook`)](#49-webhook--home-assistant-ingestion-apiwebhook)
   - [4.10 System Administration & Maintenance (`/api/v1/admin`, `/api/v1/version`)](#410-system-administration--maintenance-apiv1admin-apiv1version)
5. [CLI Administration Command Reference](#5-cli-administration-command-reference)
6. [Pagination, Filtering & Concurrency Rules](#6-pagination-filtering--concurrency-rules)

---

## 1. Overview & Protocols

### Base URLs
- **Production Server**: `http://<host>:8000`
- **Local Development**: `http://localhost:8000`
- **Interactive Swagger Documentation**: `http://localhost:8000/docs`
- **OpenAPI 3.0 Schema**: `http://localhost:8000/openapi.json`

### Protocols & Transport
- **Transport**: Standard HTTP/1.1 and HTTP/2 over TLS (or unencrypted HTTP on secure private LANs).
- **Default Payload Format**: `application/json` (UTF-8 encoded).
- **Exceptions**:
  - `POST /auth/token` requires `application/x-www-form-urlencoded`.
  - Database restore (`POST /api/v1/admin/restore`) requires `multipart/form-data`.
  - Database backup download (`GET /api/v1/admin/backup/latest`) streams binary `application/octet-stream`.

---

## 2. Authentication & Security

The system implements dual-layer authentication supporting interactive sessions and persistent background automation.

### 2.1 JWT Bearer Token Authentication
Used by the web frontend and interactive REST clients.

1. **Obtain Token Pair**: Submit credentials via `POST /auth/token`.
2. **Access Protected Endpoints**: Provide access token in HTTP header:
   ```http
   Authorization: Bearer <access_token>
   ```
3. **Automatic Renewal**: When an access token expires (default 15 minutes), exchange the refresh token via `POST /auth/refresh`. The frontend manages concurrent requests during renewal via an internal queuing mechanism (`refreshQueue`).

### 2.2 API Key Authentication (Webhooks & Persistent Integrations)
Ideal for Home Assistant automations, cron jobs, and hardware microcontrollers.

- **Via HTTP Header** (Preferred):
  ```http
  X-Webhook-Secret: sec_key_your_generated_secret_key
  ```
- **Via Query Parameter** (Fallback / URL auto-login):
  ```http
  GET /api/v1/users/me?api_key=sec_key_your_generated_secret_key
  ```

---

## 3. Error Envelopes & Response Codes

### 3.1 HTTP Status Codes
| HTTP Code | Name | Description |
| :--- | :--- | :--- |
| `200 OK` | Succeeded | Standard response for successful GET, PUT, or POST commands returning content. |
| `201 Created` | Created | Resource successfully created. |
| `204 No Content` | No Content | Action succeeded; no body returned (e.g. DELETE operations). |
| `400 Bad Request` | Client Error | Business validation failure (e.g., duplicate username, password mismatch). |
| `401 Unauthorized` | Unauthorized | Missing, expired, or invalid credentials/token. |
| `403 Forbidden` | Forbidden | Insufficient user rights (e.g., non-admin calling `/admin/*`). |
| `404 Not Found` | Not Found | Requested entity ID, barcode, or food item does not exist. |
| `422 Unprocessable`| Validation Failure | Request body failed schema validation. |
| `500 Server Error` | Server Error | Uncaught server exception. |

### 3.2 Error Payloads

#### Schema Validation Failure (HTTP 422)
```json
{
  "detail": [
    {
      "loc": ["body", "systolic"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### Application Logic Failure (HTTP 400 / 401 / 404)
```json
{
  "detail": "Item 'Greek Yogurt' not found in nutrition cache."
}
```

---

## 4. REST API Endpoint Reference

### 4.1 Authentication & Token Lifecycle (`/auth`)

#### `POST /auth/token`
Obtains a JWT access and refresh token pair using username and password.

- **Authentication**: None (Public)
- **Headers**: `Content-Type: application/x-www-form-urlencoded`
- **Form Body**:
  - `username` (string, required): Registered user account name.
  - `password` (string, required): Account plaintext password.
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer"
  }
  ```
- **Errors**: `401 Unauthorized` (Incorrect username or password).

---

#### `POST /auth/refresh`
Issues a fresh JWT token pair using an active refresh token.

- **Authentication**: None (Public)
- **Request Body**:
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsIn..."
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer"
  }
  ```
- **Errors**: `401 Unauthorized` (Invalid or expired refresh token).

---

### 4.2 User Management & Personal API Keys (`/api/v1/users`)

#### `POST /api/v1/users/`
Creates a new user profile account.

- **Authentication**: None (Public)
- **Request Body**:
  ```json
  {
    "username": "jane_doe",
    "password": "StrongPassword123!",
    "weight_kg": 68.0,
    "height_cm": 168.0,
    "unit_system": "METRIC",
    "birth_year": 1992,
    "date_of_birth": "1992-04-12",
    "gender": "F",
    "goal_weight_kg": 63.0,
    "calorie_goal": 1800,
    "timezone": "America/New_York",
    "theme_preference": "SYSTEM"
  }
  ```
- **Response (200 OK)**: Complete user profile JSON object.
- **Errors**: `400 Bad Request` (Username already registered).

---

#### `GET /api/v1/users/me`
Fetches the current authenticated user's profile and schedule settings.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Response (200 OK)**:
  ```json
  {
    "id": 1,
    "username": "jane_doe",
    "weight_kg": 68.0,
    "height_cm": 168.0,
    "unit_system": "METRIC",
    "birth_year": 1992,
    "date_of_birth": "1992-04-12",
    "gender": "F",
    "goal_weight_kg": 63.0,
    "calorie_goal": 1800,
    "timezone": "America/New_York",
    "theme_preference": "SYSTEM",
    "is_admin": false,
    "window_morning_start": "06:00:00",
    "window_afternoon_start": "12:00:00",
    "window_evening_start": "17:00:00",
    "window_bedtime_start": "21:00:00",
    "meal_breakfast_start": "09:00:00",
    "meal_lunch_start": "11:00:00",
    "meal_dinner_start": "15:00:00",
    "meal_dinner_end": "19:00:00"
  }
  ```

---

#### `PUT /api/v1/users/me`
Updates profile settings, meal schedules, and physical dimensions.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**: Partial or full `UserUpdate` object (e.g. `{"calorie_goal": 1950, "theme_preference": "DARK"}`).
- **Response (200 OK)**: Updated user object.

---

#### `PUT /api/v1/users/me/password`
Updates the password for the active session user.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**:
  ```json
  {
    "current_password": "CurrentPassword123!",
    "new_password": "NewUltraSecurePassword456!",
    "confirm_password": "NewUltraSecurePassword456!"
  }
  ```
- **Response (200 OK)**: `{"message": "Password updated successfully"}`
- **Errors**: `400 Bad Request` (Invalid current password or confirmation mismatch).

---

#### `GET /api/v1/users/me/keys`
Lists all active API keys belonging to the user.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Response (200 OK)**:
  ```json
  [
    {
      "id": 1,
      "name": "Home Assistant Node",
      "created_at": "2023-10-25T14:20:00",
      "last_used_at": "2023-10-27T08:12:00"
    }
  ]
  ```

---

#### `POST /api/v1/users/me/keys`
Generates a persistent API key for automations.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**: `{"name": "Home Assistant Node"}`
- **Response (200 OK)**:
  ```json
  {
    "id": 1,
    "name": "Home Assistant Node",
    "api_key": "sec_key_384729374029348239048",
    "created_at": "2023-10-25T14:20:00"
  }
  ```
  *(Important: `api_key` plaintext is only revealed once upon generation).*

---

#### `DELETE /api/v1/users/me/keys/{key_id}`
Revokes an active API key.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `key_id` (integer)
- **Response (200 OK)**: `{"message": "API Key revoked successfully"}`

---

### 4.3 Health & Activity Logging (`/api/v1/log`)

#### `POST /api/v1/log/bp`
Logs a blood pressure reading.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**:
  ```json
  {
    "systolic": 118,
    "diastolic": 78,
    "pulse": 68,
    "location": "Left Arm",
    "stress_level": 2,
    "meds_taken_before": "None",
    "timestamp": "2023-10-27T08:15:00Z"
  }
  ```
- **Response (200 OK)**: Persisted blood pressure log object.

---

#### `GET /api/v1/log/history/bp`
Retrieves historical blood pressure records.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Query Parameter**: `limit` (integer, default: `50`)
- **Response (200 OK)**: Array of blood pressure records ordered descending by timestamp.

---

#### `POST /api/v1/log/exercise`
Logs a physical exercise or workout activity.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**:
  ```json
  {
    "activity_type": "Cycling",
    "duration_minutes": 45,
    "calories_burned": 380.0,
    "timestamp": "2023-10-27T17:30:00Z"
  }
  ```
- **Response (200 OK)**: `{"message": "Exercise logged", "calories_burned": 380.0}`

---

#### `GET /api/v1/log/history/exercise`
Retrieves past workout logs.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Query Parameter**: `limit` (integer, default: `50`)
- **Response (200 OK)**: Array of exercise log items.

---

#### `PUT /api/v1/log/exercise/{log_id}`
Updates an existing exercise entry.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `log_id` (integer)
- **Request Body**: Exercise payload.
- **Response (200 OK)**: Updated exercise record.

---

#### `DELETE /api/v1/log/exercise/{log_id}`
Deletes an exercise entry.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `log_id` (integer)
- **Response (200 OK)**: `{"message": "Exercise log deleted"}`

---

#### `PUT /api/v1/log/food/{log_id}`
Updates an existing food log entry.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `log_id` (integer)
- **Request Body**:
  ```json
  {
    "quantity": 1.5,
    "serving_size": "1 cup",
    "meal_id": "Lunch"
  }
  ```
- **Response (200 OK)**: Updated food log item.

---

#### `DELETE /api/v1/log/food/{log_id}`
Deletes a logged food item.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `log_id` (integer)
- **Response (200 OK)**: `{"message": "Food log deleted"}`

---

#### `GET /api/v1/log/summary`
Calculates aggregated daily nutrition and vitals breakdown.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Query Parameter**: `date_str` (string, format `YYYY-MM-DD`, optional, defaults to today in user's timezone)
- **Response (200 OK)**:
  ```json
  {
    "date": "2023-10-27",
    "calories_consumed": 2100.0,
    "calorie_goal": 2000,
    "calories_burned": 380.0,
    "net_calories": 1720.0,
    "protein_g": 135.0,
    "fat_g": 65.0,
    "carbs_g": 240.0,
    "fiber_g": 28.0,
    "sodium_mg": 1950.0,
    "food_logs": [ ... ],
    "exercises": [ ... ],
    "bp_logs": [ ... ]
  }
  ```

---

#### `GET /api/v1/log/reports/compliance`
Generates a 30-day medication compliance report.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Response (200 OK)**: Compliance metrics grouped by tracked medications.

---

#### `GET /api/v1/log/reports/adherence`
Generates a detailed adherence breakdown for scheduled medications.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Response (200 OK)**: Percentage adherence scores categorized across daily schedule windows.

---

### 4.4 Medications & Prescribers (`/api/v1/medications`, `/api/v1/prescribers`)

#### `GET /api/v1/medications/`
Lists all user medications.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Query Parameters**: `skip` (int, default: 0), `limit` (int, default: 100)
- **Response (200 OK)**: Array of medication models.

---

#### `POST /api/v1/medications/`
Registers a new medication.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**:
  ```json
  {
    "name": "Atorvastatin",
    "dosage": "20mg",
    "form": "Tablet",
    "inventory": 60,
    "refill_threshold": 10,
    "refill_quantity": 30,
    "is_tracked": true,
    "sched_morning": false,
    "sched_afternoon": false,
    "sched_evening": true,
    "sched_bedtime": false,
    "prescriber_id": 1,
    "start_date": "2023-01-01",
    "end_date": null
  }
  ```
- **Response (200 OK)**: Created medication model.

---

#### `PUT /api/v1/medications/{med_id}`
Updates details of an existing medication.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `med_id` (integer)
- **Request Body**: Medication fields to modify.
- **Response (200 OK)**: Updated medication object.

---

#### `POST /api/v1/medications/{med_id}/refill`
Increments inventory count for a medication.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `med_id` (integer)
- **Request Body**: `{"quantity": 30}`
- **Response (200 OK)**: Updated medication record with new inventory total.

---

#### `GET /api/v1/medications/log`
Retrieves medication dose logs for a given date.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Query Parameter**: `date_str` (string, `YYYY-MM-DD`, optional)
- **Response (200 OK)**: Array of dose log entries.

---

#### `PUT /api/v1/medications/log/{log_id}`
Updates a medication dose log.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `log_id` (integer)
- **Response (200 OK)**: Updated dose log entry.

---

#### `DELETE /api/v1/medications/log/{log_id}`
Deletes a medication dose log entry.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `log_id` (integer)
- **Response (200 OK)**: `{"message": "Medication log deleted"}`

---

#### `GET /api/v1/prescribers/`
Lists prescribers associated with the user account.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Query Parameters**: `skip` (int, default: 0), `limit` (int, default: 100)
- **Response (200 OK)**: Array of prescriber objects.

---

#### `POST /api/v1/prescribers/`
Creates a prescriber contact profile.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**:
  ```json
  {
    "name": "Dr. Emily Taylor",
    "specialty": "Internal Medicine",
    "phone": "555-0144",
    "email": "dr.taylor@clinic.org",
    "address": "404 Health Way, Suite 200"
  }
  ```
- **Response (200 OK)**: Created prescriber record.

---

### 4.5 Medical History (`/api/v1/medical`)

#### `GET /api/v1/medical/allergies`
Lists allergy entries.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Response (200 OK)**: Array of allergy records.

---

#### `POST /api/v1/medical/allergies`
Logs a new allergy.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**:
  ```json
  {
    "allergen": "Sulfa Drugs",
    "severity": "Moderate",
    "reaction": "Skin rash and itching",
    "notes": "Observed during 2021 prescription"
  }
  ```
- **Response (200 OK)**: Created allergy record.

---

#### `PUT /api/v1/medical/allergies/{allergy_id}`
Updates an allergy record.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `allergy_id` (integer)
- **Response (200 OK)**: Updated allergy object.

---

#### `DELETE /api/v1/medical/allergies/{allergy_id}`
Deletes an allergy entry.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `allergy_id` (integer)
- **Response (204 No Content)**: Empty body.

---

#### `GET /api/v1/medical/vaccinations`
Lists vaccination logs.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Response (200 OK)**: Array of vaccination records.

---

#### `POST /api/v1/medical/vaccinations`
Logs a vaccination administration.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**:
  ```json
  {
    "vaccine_type": "Tetanus, Diphtheria, Pertussis (Tdap)",
    "date_administered": "2022-06-15",
    "expiration_date": "2032-06-15",
    "lot_number": "TD99482",
    "administered_by": "County Health Department",
    "notes": "10-year booster"
  }
  ```
- **Response (200 OK)**: Created vaccination record.

---

#### `GET /api/v1/medical/reports/vaccinations`
Generates a vaccine schedule status report.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Response (200 OK)**: Categorized vaccination status and renewal reminders.

---

### 4.6 Nutrition Services v1 & v2 (`/api/v1/nutrition`, `/api/v2/nutrition`)

#### `POST /api/v1/nutrition/`
Creates a custom item in the local nutrition database.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**:
  ```json
  {
    "food_name": "Rolled Oats",
    "brand": "Quaker",
    "barcode": "030000010408",
    "calories": 150.0,
    "protein": 5.0,
    "fat": 2.5,
    "carbs": 27.0,
    "fiber": 4.0,
    "sodium": 0.0,
    "is_staple": true
  }
  ```
- **Response (200 OK)**: Created `NutritionCache` item.

---

#### `GET /api/v1/nutrition/list`
Lists cached nutrition records with optional search and staple filtering.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Query Parameters**:
  - `skip` (int, default: 0)
  - `limit` (int, default: 50)
  - `search` (string, optional): Search food name or brand.
  - `include_hidden` (boolean, default: false)
  - `is_staple` (boolean, optional): Filter staple items (`true`/`false`).
- **Response (200 OK)**: Array of `NutritionCache` objects.

---

#### `GET /api/v1/nutrition/search`
Searches food items across both local cache and Open Food Facts.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Query Parameters**:
  - `query` (string, required)
  - `scope` (string, default: `all`)
- **Response (200 OK)**: Array of matching food items.

---

#### `GET /api/v1/nutrition/{food_id}`
Retrieves a cached food item by ID.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `food_id` (integer)
- **Response (200 OK)**: `NutritionCache` object.

---

#### `PUT /api/v1/nutrition/{food_id}`
Updates cached food item nutrients, staple status, or serving metadata.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `food_id` (integer)
- **Response (200 OK)**: Updated `NutritionCache` object.

---

#### `DELETE /api/v1/nutrition/{food_id}`
Deletes or marks cached food item as hidden.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `food_id` (integer)
- **Response (200 OK)**: `{"message": "Item deleted"}`

---

#### `POST /api/v1/nutrition/log`
Logs food consumption to the daily ledger (Schema v1).

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**:
  ```json
  {
    "food_name": "Rolled Oats",
    "barcode": "030000010408",
    "serving_size": "1/2 cup dry",
    "quantity": 1.0,
    "meal_id": "Breakfast",
    "timestamp": "2023-10-27T08:00:00Z"
  }
  ```
- **Response (200 OK)**: Created food log entry.

---

#### `POST /api/v1/nutrition/ask-gemini`
Generates personalized nutrition advice via Google Gemini 2.5 Flash using daily logs and pantry staples.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**: `{"date_str": "2023-10-27"}`
- **Response (200 OK)**:
  ```json
  {
    "advice": "Based on your daily summary: You have consumed 1,450 kcal of your 2,000 kcal target..."
  }
  ```

---

#### `GET /api/v2/nutrition/generate_upc`
Generates a unique local UPC barcode number for custom foods and homemade recipes.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Response (200 OK)**: `{"upc": "200000000142"}`

---

#### `GET /api/v2/nutrition/lookup/{barcode}`
Retrieves structured Nutrition v2 metadata (macros, micros, health analysis) by barcode.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `barcode` (string)
- **Response (200 OK)**:
  ```json
  {
    "barcode": "030000010408",
    "food_item": {
      "name": "Rolled Oats",
      "brand": "Quaker"
    },
    "serving_info": {
      "serving_size_unit": "g",
      "serving_weight_grams": 40.0,
      "serving_volume_ml": null
    },
    "macros": {
      "calories": 150.0,
      "protein": 5.0,
      "fat": 2.5,
      "carbs": 27.0,
      "fiber": 4.0,
      "sodium": 0.0
    },
    "micros": {
      "cholesterol": 0.0,
      "total_sugars": 1.0,
      "added_sugars": 0.0,
      "vitamin_d": 0.0,
      "calcium": 20.0,
      "iron": 1.5,
      "potassium": 150.0
    },
    "analysis": {
      "health_score": "A",
      "health_insight": "Excellent source of soluble fiber.",
      "pairing_tip": "Pairs well with blueberries and cinnamon."
    },
    "metadata": {
      "is_staple": true,
      "on_shopping_list": false
    }
  }
  ```

---

#### `POST /api/v2/nutrition/log`
Logs food consumption using structured Nutrition v2 payload.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Query Parameter**: `check_existence` (boolean, default: false)
- **Request Body**: NutritionLogV2 schema object.
- **Response (200 OK)**: Created food log entry.

---

### 4.7 Recipes Management (`/api/v1/recipes`)

#### `GET /api/v1/recipes/`
Lists all recipes authored by the user.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Response (200 OK)**: Array of recipe objects including ingredients breakdown.

---

#### `POST /api/v1/recipes/`
Creates a multi-ingredient recipe.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**:
  ```json
  {
    "name": "Overnight Oats",
    "servings": 1,
    "instructions": "Combine oats with almond milk and chia seeds. Refrigerate overnight.",
    "ingredients": [
      {
        "nutrition_cache_id": 14,
        "quantity": 40.0,
        "unit": "g"
      },
      {
        "nutrition_cache_id": 22,
        "quantity": 200.0,
        "unit": "ml"
      }
    ]
  }
  ```
- **Response (200 OK)**: Created recipe record.

---

#### `GET /api/v1/recipes/{recipe_id}`
Retrieves single recipe details.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `recipe_id` (integer)
- **Response (200 OK)**: Recipe object.

---

#### `PUT /api/v1/recipes/{recipe_id}`
Updates recipe metadata, servings, or ingredient composition.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `recipe_id` (integer)
- **Response (200 OK)**: Updated recipe object.

---

#### `DELETE /api/v1/recipes/{recipe_id}`
Deletes a recipe.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Path Parameter**: `recipe_id` (integer)
- **Response (200 OK)**: `{"message": "Recipe deleted"}`

---

### 4.8 Shopping List Synchronization (`/api/v1/shopping-list`)

#### `POST /api/v1/shopping-list/items`
Marks a cached nutrition item as present on the shopping list.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**: `{"food_name": "Rolled Oats"}`
- **Response (200 OK)**: `{"message": "Item added to shopping list", "food_name": "Rolled Oats"}`
- **Errors**: `404 Not Found` (Item not found in nutrition database).

---

#### `DELETE /api/v1/shopping-list/items`
Removes an item from the shopping list.

- **Authentication**: Bearer Token or `X-Webhook-Secret`
- **Request Body**: `{"food_name": "Rolled Oats"}`
- **Response (200 OK)**: `{"message": "Item removed from shopping list", "food_name": "Rolled Oats"}`
- **Errors**: `404 Not Found` (Item not found in nutrition database).

---

### 4.9 Webhook & Home Assistant Ingestion (`/api/webhook`)

#### `POST /api/webhook/health`
Universal ingestion endpoint for Home Assistant scripts, automations, and external IoT sensors.

- **Authentication**: `X-Webhook-Secret` header or `?api_key=` query parameter required.
- **Request Body Envelopes**:

##### Example: Blood Pressure
```json
{
  "data_type": "BLOOD_PRESSURE",
  "payload": {
    "systolic": 120,
    "diastolic": 80,
    "pulse": 72
  }
}
```

##### Example: Weight Reading
```json
{
  "data_type": "WEIGHT",
  "payload": {
    "weight_kg": 74.5
  }
}
```

##### Example: Scheduled Window Medication Dose
```json
{
  "data_type": "MEDICATION_WINDOW_TAKEN",
  "payload": {
    "window": "morning"
  }
}
```
*(Logs doses for all active, tracked medications assigned to the `morning` schedule window for the current date).*

##### Example: Exercise Session
```json
{
  "data_type": "EXERCISE_SESSION",
  "payload": {
    "activity_type": "Running",
    "duration_minutes": 30,
    "calories_burned": 320
  }
}
```

- **Response (200 OK)**: `{"status": "success", "message": "Logged successfully"}`
- **Errors**: `400 Bad Request` (Unsupported `data_type` or invalid payload), `401 Unauthorized`.

---

#### `GET /api/webhook/nutrition/{barcode}`
Returns concise nutritional facts formatted for Home Assistant notifications or voice assistant responses.

- **Authentication**: `X-Webhook-Secret` header or `?api_key=` query parameter required.
- **Path Parameter**: `barcode` (string)
- **Response (200 OK)**:
  ```json
  {
    "found": true,
    "food_name": "Rolled Oats",
    "calories": 150,
    "protein": 5,
    "fat": 2.5,
    "carbs": 27
  }
  ```

---

### 4.10 System Administration & Maintenance (`/api/v1/admin`, `/api/v1/version`)

All `/api/v1/admin/*` endpoints require the authenticated user to possess `is_admin = True`.

#### `GET /api/v1/admin/mqtt_status`
Reports current MQTT client broker connection state.

- **Authentication**: Bearer Token or `X-Webhook-Secret` (Admin required)
- **Response (200 OK)**:
  ```json
  {
    "connected": true,
    "broker": "192.168.1.50",
    "port": 1883
  }
  ```

---

#### `POST /api/v1/admin/key`
Sets the encryption passphrase for encrypted database backups.

- **Authentication**: Bearer Token or `X-Webhook-Secret` (Admin required)
- **Request Body**: `{"key": "mySecretPassphrase"}`
- **Response (200 OK)**: `{"message": "Backup key set successfully"}`

---

#### `POST /api/v1/admin/backup`
Triggers generation of an encrypted snapshot of `health_app.db`.

- **Authentication**: Bearer Token or `X-Webhook-Secret` (Admin required)
- **Response (200 OK)**:
  ```json
  {
    "message": "Backup created successfully",
    "filename": "backup_20231027_120000.enc"
  }
  ```

---

#### `GET /api/v1/admin/backup/latest`
Streams and downloads the most recently generated encrypted database backup file.

- **Authentication**: Bearer Token or `X-Webhook-Secret` (Admin required)
- **Response (200 OK)**: File stream with `Content-Type: application/octet-stream`.

---

#### `POST /api/v1/admin/restore`
Restores database contents from an uploaded encrypted backup file.

- **Authentication**: Bearer Token or `X-Webhook-Secret` (Admin required)
- **Headers**: `Content-Type: multipart/form-data`
- **Form Data**: `file` (binary payload)
- **Response (200 OK)**: `{"message": "Database restored successfully"}`

---

#### `GET /api/v1/version`
Returns the application build release version and build timestamp.

- **Authentication**: None (Public)
- **Response (200 OK)**:
  ```json
  {
    "version": "1.0.0",
    "date": "2023-10-27"
  }
  ```

---

#### `GET /`
Serves the single-page application dashboard (`app/static/index.html`).

- **Authentication**: None (Public)
- **Response (200 OK)**: HTML document.

---

## 5. CLI Administration Command Reference

Administrative operations can be executed directly on the host using the CLI tool in `app.cli`.

Always execute CLI commands with `PYTHONPATH=.` from the application root:

```bash
PYTHONPATH=. ./.venv/bin/python -m app.cli <subcommand> [flags]
```

### Available Subcommands & Options

#### `create-user`
Creates a new user profile with password hashing.

| Flag | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `--name` | string | Yes | Username for the new profile. |
| `--password` | string | Yes | Plaintext initial password. |
| `--weight` | float | Yes | Weight (kg if metric, lbs if imperial). |
| `--height` | float | Yes | Height (cm if metric, inches if imperial). |
| `--unit-system`| string | No | `metric` (default) or `imperial`. |

#### `make-admin`
Grants or revokes administrative status for a user.

| Flag | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `--user-id` | integer | Yes | Target user identifier. |
| `--revoke` | flag | No | If specified, revokes admin privileges instead of granting. |

#### `create-apikey`
Generates a persistent API key for a specified user.

| Flag | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `--user-id` | integer | Yes | User ID to own the generated key. |
| `--name` | string | Yes | Human-readable label for key identification. |

#### `revoke-apikey`
Deactivates an existing API key.

| Flag | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `--key-id` | integer | Yes | Unique ID of the API key to deactivate. |

#### `reset-password`
Forces a password reset for a given user account.

| Flag | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `--user-id` | integer | Yes | Target user identifier. |
| `--password` | string | Yes | New plaintext password. |

---

## 6. Pagination, Filtering & Concurrency Rules

1. **Zero-Indexed Pagination**:
   Endpoints returning lists (`/api/v1/medications/`, `/api/v1/prescribers/`, `/api/v1/nutrition/list`) accept `skip` (default `0`) and `limit` (default `50` or `100`).
2. **Case-Insensitive Search**:
   The `/api/v1/nutrition/list` endpoint accepts `search=<query>` matching food titles or brands using case-insensitive SQL `LIKE` queries.
3. **Daily Schedule Window Idempotency**:
   The application strictly forbids duplicate medication logs for the same medication, within the same window, on the same calendar day. The calculation is evaluated against the user's localized date (`user.timezone`).
4. **Token Refresh Concurrency**:
   In high-frequency API environments, multiple client requests may receive `401 Unauthorized` simultaneously. Clients must queue concurrent refresh attempts to ensure only a single `/auth/refresh` request is in-flight at any moment.
