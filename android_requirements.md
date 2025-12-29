# Android App Requirements

This document outlines the requirements and technical specifications for building an Android companion app for the Health Tracker.

## 1. Authentication Strategy

The app should **never** store the user's password locally. Instead, it should use the Token-Based Authentication flow (OAuth2-style).

### Flow
1.  **Login:** User enters username/password.
2.  **Exchange:** App POSTs credentials to `/auth/token`.
3.  **Storage:** Server returns an `access_token` (short-lived, 30 min) and a `refresh_token` (long-lived, 30 days). Store these securely using **EncryptedSharedPreferences**.
4.  **Usage:** Attach `access_token` to every API request header: `Authorization: Bearer <token>`.
5.  **Refresh:** If the server returns `401 Unauthorized`, the app should:
    *   Call `/auth/refresh` with the `refresh_token` (query param).
    *   Receive a new `access_token`.
    *   Retry the original request.
    *   If the refresh fails (e.g., token expired), force the user to log in again.

### Endpoints

#### Login
*   **URL:** `POST /auth/token`
*   **Body (Form Data):** `username=<user>`, `password=<pass>`
*   **Response:**
    ```json
    {
      "access_token": "eyJhbG...",
      "refresh_token": "eyJhbG...",
      "token_type": "bearer"
    }
    ```

#### Refresh Token
*   **URL:** `POST /auth/refresh`
*   **Body (JSON):** `{"refresh_token": "<stored_refresh_token>"}`
*   **Response:** Same as Login (returns new access token).

---

## 2. API Integration

The app should interact with the server via the REST API at `/api/v1`.

### Library Recommendation
*   **Networking:** Retrofit + OkHttp.
*   **JSON Parsing:** Moshi or Gson.
*   **Async:** Kotlin Coroutines.

### Key Endpoints

| Feature | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **User Profile** | `GET` | `/api/v1/users/me` | Get user settings & profile. |
| **Log BP** | `POST` | `/api/v1/log/bp` | Log a Blood Pressure reading. |
| **BP History** | `GET` | `/api/v1/log/history/bp` | Get last 50 BP logs. |
| **Log Meds** | `POST` | `/api/v1/webhook/health` | (Rec.) Log medication taken. |
| **Daily Summary**| `GET` | `/api/v1/log/summary` | Get today's dashboard data (Calories, Macros, BP). |
| **Med Logs** | `GET` | `/api/v1/medications/log` | Get logs for a specific day. |

### JSON Examples

#### Log Blood Pressure
**POST** `/api/v1/log/bp`
```json
{
  "systolic": 120,
  "diastolic": 80,
  "pulse": 72,
  "location": "Left Arm",
  "stress_level": 2,
  "meds_taken_before": "None"
}
```

#### Log Medication (via Webhook Endpoint)
**POST** `/api/v1/webhook/health`
Header: `X-Webhook-Secret: <your_api_key>` (Or use standard auth if calling internal APIs directly, though webhook is robust).
*Better Strategy for App:* Use the internal API if authenticated as User.
**POST** `/api/v1/medications/log` (Internal logic might need verification, currently webhook is primary for "taking" action, but internal logs exist).
*Actually, the most robust "User Action" for taking meds is currently the Webhook or direct DB insertion via service.*

**Recommendation:** For the app, use the `MedicationTakenPayload` structure but you might need to adapt if not using the webhook endpoint.
*Correction:* The app can simply use the standard CRUD or Webhook. If using Webhook, it needs an API Key. If using Bearer Token, you might need to ensure an endpoint exists for "Taking" a med by ID.
*Current API:* `POST /api/v1/webhook/health` handles `MEDICATION_TAKEN`.
*There isn't a direct `POST /api/v1/medications/{id}/take` endpoint exposed for UI users in the routers viewed so far, except via Webhook.*
**Action Item for App Dev:** You may want to add a direct "Take" endpoint for authenticated users, or just use the webhook endpoint with the user's API key (which can be fetched from `/api/v1/users/me` if added to the response, or generated).

#### Daily Summary Response
**GET** `/api/v1/log/summary`
```json
{
  "blood_pressure": "120/80",
  "calories_consumed": 1500,
  "calories_burned": 400,
  "macros": {
    "protein": 100,
    "fat": 50,
    "carbs": 150,
    "fiber": 25
  },
  "food_logs": [],
  "exercises": []
}
```

## 3. Security Checklist for Android

1.  **Network Security Config:** Ensure cleartext traffic is disabled (only HTTPS) in production.
2.  **Proguard/R8:** Enable obfuscation to hide API logic.
3.  **Biometrics:** Optional: Use BiometricPrompt to unlock the app before retrieving the tokens from storage.
