# Android App Requirements

This document outlines the requirements and technical specifications for building an Android companion app for the Health Tracker. The app should replicate the features of the web frontend, utilizing the existing REST API.

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

### Security Checklist
1.  **Network Security Config:** Ensure cleartext traffic is disabled (only HTTPS) in production.
2.  **Proguard/R8:** Enable obfuscation.
3.  **Biometrics:** Optional: Use BiometricPrompt to unlock the app before retrieving tokens.

---

## 2. Screens & Features

The app should implement the following screens, corresponding to the web tabs.

### A. Dashboard (Home)
*   **Date Navigation:** Allow user to switch days (Previous/Next day). Defaults to "Today".
*   **Daily Summary Cards:**
    *   Blood Pressure (Latest entry for selected day).
    *   Calories In vs. Calories Out vs. Net.
*   **Health Gauges:** Visual gauges for Daily Goals.
    *   Calories (Goal from profile).
    *   Macros: Protein, Fat, Carbs, Fiber (Targets calculated based on profile/gender).
*   **Activity Log:**
    *   **Medications Taken:** List of meds taken on selected day.
    *   **Exercises:** List of exercises on selected day.
    *   **Food Log:** List of food entries on selected day.
    *   *Action:* Clicking "Manage" on these lists should open a detail view to Edit/Delete logs.

### B. Medications
*   **List View:** Display all medications.
    *   Show Name, Frequency, Schedule (M/A/E/B), Type, Stock, Refills.
    *   *Action:* "Refill Received" button (Calls `POST /api/v1/medications/{id}/refill`).
    *   *Action:* "Edit" button (Opens Edit Modal).
*   **Add/Edit Medication:** Form to create or update medication.
    *   Fields: Name, Frequency, Type (RX/OTC), Inventory, Refills, Refill Quantity, Start/End Dates.
    *   Schedule Checkboxes: Morning, Afternoon, Evening, Bedtime.
*   **Log Dose:** (Usually handled via Webhook or implicit logic, but app can provide a manual "Take Now" button if API supports it, currently primarily tracking history).

### C. Nutrition
*   **Log Food:**
    *   **Search:** Search local database (`GET /api/v1/nutrition/search`).
    *   **Manual Entry:** If search fails, allow manual entry of Name/Calories.
    *   **Barcode Scanner:** (Optional but recommended) Scan barcode, query `/api/v1/webhook/nutrition/{barcode}`, then pre-fill form.
    *   **Form:** Meal (Breakfast/Lunch/Dinner/Snack), Serving Size, Quantity.
*   **Create Custom Food:** Form to add new item to local cache (Name, Barcode, Macros).

### D. Health Logs
*   **Log Blood Pressure:** Form for Systolic, Diastolic, Pulse.
*   **Log Weight:** Form for Weight (respects User Unit Preference).
*   **Log Exercise:** Form for Activity Type, Duration, Calories (optional).
*   **Log Vaccination:** Form for Vaccine Type, Date Administered.
*   **History Views:**
    *   Recent Exercises (List).
    *   Vaccination Report (List with Status).
    *   Allergies List (List).

### E. Reports
*   **User Profile Summary:** Name, DOB, Weight.
*   **Medication Compliance:**
    *   Overall % for last 30 days.
    *   Missed vs Taken counts.
    *   Detailed breakdown table per medication.
*   **Blood Pressure History:** List of last 50 readings. (Optional: Export CSV).

### F. Settings
*   **Profile:** Edit Name, Unit System (Metric/Imperial), Timezone, DOB, Gender, Height, Weight, Goals.
*   **Schedule Windows:** Set start times for Morning, Afternoon, Evening, Bedtime.
*   **Medical:** Manage Allergies (Add/Edit/Delete).
*   **Security:** Change Password.
*   **App Theme:** Light/Dark/System.
*   **Admin (If User is Admin):**
    *   MQTT Status.
    *   Backup/Restore Database.
    *   Update Encryption Key.

---

## 3. API Reference

Base URL: `http://<server>:8000/api/v1` (typical).

### Authentication
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/auth/token` | Login. Returns `access_token`, `refresh_token`. |
| `POST` | `/auth/refresh` | Refresh access token. Body: `{"refresh_token": "..."}` |

### Users & Profile
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/users/me` | Get current user profile & settings. |
| `PUT` | `/api/v1/users/me` | Update profile (Weight, Units, Timezone, etc). |
| `PUT` | `/api/v1/users/me/password` | Change password. |

### Dashboard & Health Logs
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/log/summary` | **Dashboard Data.** Params: `date_str` (YYYY-MM-DD). Returns BP, Calories, Macros, Lists. |
| `POST` | `/api/v1/log/bp` | Log Blood Pressure. |
| `GET` | `/api/v1/log/history/bp` | Get BP History (limit 50). |
| `POST` | `/api/v1/log/exercise` | Log Exercise. |
| `GET` | `/api/v1/log/history/exercise` | Get Exercise History. |
| `PUT` | `/api/v1/log/exercise/{id}` | Update Exercise Log. |
| `DELETE`| `/api/v1/log/exercise/{id}` | Delete Exercise Log. |
| `PUT` | `/api/v1/log/food/{id}` | Update Food Log. |
| `DELETE`| `/api/v1/log/food/{id}` | Delete Food Log. |

### Medications
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/medications/` | List all medications (definitions). |
| `POST` | `/api/v1/medications/` | Create new medication. |
| `PUT` | `/api/v1/medications/{id}` | Update medication. |
| `POST` | `/api/v1/medications/{id}/refill`| Record refill (Update stock). |
| `GET` | `/api/v1/medications/log` | Get logs for a day. Params: `date_str`. |
| `PUT` | `/api/v1/medications/log/{id}` | Update a specific dose log (timestamp/window). |
| `DELETE`| `/api/v1/medications/log/{id}` | Delete a dose log (Increments stock). |
| `POST` | `/api/v1/webhook/health` | **Take Med:** Payload `data_type: "MEDICATION_TAKEN"`. |

### Nutrition
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/nutrition/search` | Search local food cache. Query param: `query`. |
| `POST` | `/api/v1/nutrition/` | Create custom food (Manual). |
| `POST` | `/api/v1/nutrition/log` | Log food entry. |
| `GET` | `/api/webhook/nutrition/{barcode}`| Lookup food by barcode (OpenFoodFacts). **Note:** Requires Webhook Secret in header or auth. |

### Medical History
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/medical/allergies` | List allergies. |
| `POST` | `/api/v1/medical/allergies` | Add allergy. |
| `PUT` | `/api/v1/medical/allergies/{id}` | Update allergy. |
| `DELETE`| `/api/v1/medical/allergies/{id}` | Delete allergy. |
| `GET` | `/api/v1/medical/reports/vaccinations` | Get vaccination report. |
| `POST` | `/api/v1/medical/vaccinations` | Log vaccination. |

### Admin
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/admin/mqtt_status` | Check MQTT connection. |
| `POST` | `/api/v1/admin/backup` | Create backup. |
| `POST` | `/api/v1/admin/restore` | Restore backup (Upload file). |
| `POST` | `/api/v1/admin/key` | Set encryption key. |

## 4. Technical Notes

1.  **Timezones:** The backend stores timestamps in UTC (SQLite).
    *   **Reading:** When fetching logs (`/summary`, `/history`), convert the returned UTC ISO string to the device's Local Time for display.
    *   **Writing:** When sending timestamps (e.g., updating a log time), convert Local Time to UTC ISO string before sending.
2.  **Units:**
    *   The backend stores Weight in **kg** and Height in **cm**.
    *   Check `user.unit_system` ("METRIC" or "IMPERIAL").
    *   **Imperial:** Display Weight as `lbs` (kg * 2.20462) and Height as `ft/in`. Convert inputs back to metric before sending to API.
3.  **Offline Support:** Not strictly required for V1, but network error handling (Retry/Alert) is essential.
