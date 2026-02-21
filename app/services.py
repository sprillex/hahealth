import requests
import os
import shutil
from google import genai
from typing import Optional, List
from sqlalchemy.orm import Session
from app import models, schemas, database
from datetime import datetime, date, timedelta, time
from cryptography.fernet import Fernet
import base64
import hashlib
from datetime import timezone
import zoneinfo

class CustomNutritionService:
    def _fetch_remote_product(self, barcode: str) -> models.NutritionCache | None:
        """
        Fetches product data from external service and returns a detached NutritionCache model.
        Does NOT save to database.
        """
        base_url = os.getenv("CUSTOM_NUTRITION_URL", "http://localhost:8000")
        # Ensure base_url doesn't end with slash if we append /product/...
        if base_url.endswith("/"):
            base_url = base_url[:-1]

        url = f"{base_url}/product/{barcode}"

        try:
            response = requests.get(url, timeout=10) # Good practice to add timeout
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get("status") == "found" and "data" in resp_json:
                    data = resp_json["data"]

                    # Helper to safely get float values
                    def get_float(val):
                        if val is None: return 0.0
                        try: return float(val)
                        except (ValueError, TypeError): return 0.0

                    # Map fields
                    # JSON: upc, item_name, brand_name, srv_per_cont, serving_size
                    # Model: barcode, food_name, brand, serving_size_unit

                    new_cache = models.NutritionCache(
                        barcode=data.get("upc", barcode),
                        food_name=data.get("item_name", "Unknown"),
                        brand=data.get("brand_name"),
                        serving_size_unit=data.get("serving_size"),

                        # Base Macros
                        calories=get_float(data.get("calories")),
                        protein=get_float(data.get("protein_g")),
                        fat=get_float(data.get("fat_g")),
                        carbs=get_float(data.get("carbs_g")),
                        fiber=get_float(data.get("fiber_g")),
                        sodium=get_float(data.get("sodium_mg")), # Stored as mg

                        # Extended Macros
                        cholesterol=get_float(data.get("cholesterol_mg")),
                        total_sugars=get_float(data.get("total_sugars_g")),
                        added_sugars=get_float(data.get("added_sugars_g")),

                        # Micros
                        vitamin_d=get_float(data.get("vit_d_mcg")),
                        calcium=get_float(data.get("calcium_mg")),
                        iron=get_float(data.get("iron_mg")),
                        potassium=get_float(data.get("potassium_mg")),

                        # Analysis
                        health_score=data.get("score_color"),
                        health_insight=data.get("health_insight"),
                        pairing_tip=data.get("pairing_tip"),

                        source=resp_json.get("source", "MANUAL"),
                        is_user_visible=True
                    )
                    return new_cache
        except requests.RequestException:
            # Handle connection errors gracefully
            return None

        return None

    def find_in_cache(self, db: Session, barcode: str) -> Optional[models.NutritionCache]:
        """
        Attempts to find a product in the local cache using fuzzy matching on the barcode.
        Strategies:
        1. Exact match.
        2. Leading zero variations (up to 14 digits).
        """
        # 1. Exact Match
        cached = db.query(models.NutritionCache).filter(models.NutritionCache.barcode == barcode).first()
        if cached:
            return cached

        # 2. Fuzzy Match (Leading Zeros)
        # Only proceed if barcode looks numeric
        if not barcode.isdigit():
            return None

        # Strip leading zeros to get base
        base_barcode = barcode.lstrip('0')
        if not base_barcode: # Was all zeros
             base_barcode = "0"

        # Generate candidates (up to 14 digits, standard GTIN length)
        candidates = set()
        # We start from len(base_barcode) up to 14
        # If base is "123", we try "123", "0123", ... "00...0123"
        for i in range(len(base_barcode), 15):
             candidate = base_barcode.zfill(i)
             if candidate != barcode: # Avoid re-checking the exact input if possible
                 candidates.add(candidate)

        if not candidates:
            return None

        # Query for any of the candidates
        # Note: We pick the first one found. Ambiguity handling: First found wins.
        fuzzy_match = db.query(models.NutritionCache).filter(models.NutritionCache.barcode.in_(candidates)).first()
        return fuzzy_match

    def get_product(self, barcode: str, db: Session):
        cached = self.find_in_cache(db, barcode)
        if cached:
            return cached

        new_cache = self._fetch_remote_product(barcode)
        if new_cache:
            db.add(new_cache)
            db.commit()
            db.refresh(new_cache)
            return new_cache

        return None

class METCalculator:
    def calculate_calories(self, db: Session, user: models.User, activity_type: str, duration_minutes: float):
        default_mets = {
            "running": 9.8,
            "walking": 3.8,
            "cycling": 7.5,
            "swimming": 8.0,
            "yoga": 2.5,
            "snow shoveling": 6.0,
            "gardening": 4.0,
            "weight lifting": 6.0,
            "rowing machine": 7.0
        }
        met_entry = db.query(models.METLookup).filter(models.METLookup.activity_name == activity_type.lower()).first()
        met_value = met_entry.met_value if met_entry else default_mets.get(activity_type.lower(), 1.0)
        return (met_value * user.weight_kg * 3.5 / 200) * duration_minutes

def get_user_local_date(user: models.User, utc_dt: datetime) -> date:
    if not utc_dt: utc_dt = datetime.now(timezone.utc)
    if utc_dt.tzinfo is None: utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    try:
        user_tz = zoneinfo.ZoneInfo(user.timezone) if user.timezone else timezone.utc
    except Exception:
        user_tz = timezone.utc
    return utc_dt.astimezone(user_tz).date()

class MedicationService:
    def log_dose(self, db: Session, user_id: int, med_name: str, timestamp_taken: datetime = None, med_window: str = None):
        if not timestamp_taken: timestamp_taken = datetime.now(timezone.utc)
        med = db.query(models.Medication).filter(
            models.Medication.user_id == user_id, models.Medication.name == med_name
        ).first()
        if not med: return None, "Medication not found"
        if med.current_inventory > 0: med.current_inventory -= 1

        dose_window = None
        if med_window:
            dose_window = med_window.lower()

        dose_log = models.MedDoseLog(
            user_id=user_id, med_id=med.med_id,
            timestamp_taken=timestamp_taken, target_time_drift=0.0,
            dose_window=dose_window
        )
        db.add(dose_log)
        alert = None
        days_remaining = med.current_inventory / med.daily_doses if med.daily_doses > 0 else 999
        if days_remaining <= 7 or med.refills_remaining <= 1:
            alert = f"Refill needed for {med.name}. Days remaining: {days_remaining:.1f}, Refills: {med.refills_remaining}"
        db.commit()
        return dose_log, alert

    def delete_dose_log(self, db: Session, log_id: int, user_id: int):
        log = db.query(models.MedDoseLog).filter(models.MedDoseLog.dose_log_id == log_id, models.MedDoseLog.user_id == user_id).first()
        if not log: return False

        # Restore Inventory
        med = db.query(models.Medication).filter(models.Medication.med_id == log.med_id).first()
        if med:
            med.current_inventory += 1

        db.delete(log)
        db.commit()
        return True

    def update_dose_log(self, db: Session, log_id: int, user_id: int, updates: schemas.LogUpdate):
        log = db.query(models.MedDoseLog).filter(models.MedDoseLog.dose_log_id == log_id, models.MedDoseLog.user_id == user_id).first()
        if not log: return None

        if updates.timestamp:
            log.timestamp_taken = updates.timestamp
        if updates.dose_window:
            log.dose_window = updates.dose_window.lower()

        # If medication changed, handle inventory swap
        # Assuming we allow changing the medication type for a log?
        # Maybe complex, but let's support it if med_id is passed.
        if updates.med_id and updates.med_id != log.med_id:
            old_med = db.query(models.Medication).filter(models.Medication.med_id == log.med_id).first()
            if old_med: old_med.current_inventory += 1 # Refund old

            new_med = db.query(models.Medication).filter(models.Medication.med_id == updates.med_id).first()
            if new_med:
                new_med.current_inventory -= 1 # Deduct new
                log.med_id = updates.med_id

        db.commit()
        db.refresh(log)
        return log

class HealthLogService:
    def log_bp(self, db: Session, user_id: int, data: schemas.BPPayload):
        bp = models.BloodPressure(
            user_id=user_id, systolic=data.systolic, diastolic=data.diastolic,
            pulse=data.pulse, location=data.location, stress_level=data.stress_level,
            meds_taken_before=data.meds_taken_before, timestamp=datetime.now(timezone.utc)
        )
        db.add(bp)
        db.commit()
        db.refresh(bp)
        return bp

    def log_exercise(self, db: Session, user: models.User, data: schemas.ExercisePayload):
        met_calc = METCalculator()
        calories = data.calories_burned
        if calories is None:
            calories = met_calc.calculate_calories(db, user, data.activity_type, data.duration_minutes)
        exercise_log = models.ExerciseLog(
            user_id=user.user_id, activity_type=data.activity_type,
            duration_minutes=data.duration_minutes, calories_burned=calories
        )
        db.add(exercise_log)
        local_date = get_user_local_date(user, datetime.now(timezone.utc))
        daily_log = db.query(models.DailyLog).filter(models.DailyLog.user_id == user.user_id, models.DailyLog.date == local_date).first()
        if not daily_log:
            daily_log = models.DailyLog(user_id=user.user_id, date=local_date, total_calories_burned=0, total_calories_consumed=0)
            db.add(daily_log)
        daily_log.total_calories_burned += calories
        db.commit()
        return exercise_log # Return the ExerciseLog, not DailyLog

    def log_food(self, db: Session, user: models.User, data: schemas.FoodLogPayload):
        nut_service = CustomNutritionService()
        food_item = None

        # Fallback: if barcode is not explicitly provided but food_name looks like one
        if not data.barcode and data.food_name and data.food_name.isdigit() and len(data.food_name) > 3:
            data.barcode = data.food_name

        if data.barcode: food_item = nut_service.get_product(data.barcode, db)
        if not food_item and data.food_name:
            food_item = db.query(models.NutritionCache).filter(models.NutritionCache.food_name == data.food_name).first()

            # If manual entry matches existing cache, update it with latest macros
            if food_item and not data.barcode:
                has_macros = any(x is not None for x in [data.calories, data.protein, data.fat, data.carbs, data.fiber, data.sodium])
                if has_macros:
                     divisor = (data.quantity * data.serving_size) if (data.quantity * data.serving_size) > 0 else 1.0
                     if data.calories is not None: food_item.calories = (data.calories / divisor)
                     if data.protein is not None: food_item.protein = (data.protein / divisor)
                     if data.fat is not None: food_item.fat = (data.fat / divisor)
                     if data.carbs is not None: food_item.carbs = (data.carbs / divisor)
                     if data.fiber is not None: food_item.fiber = (data.fiber / divisor)
                     if data.sodium is not None: food_item.sodium = (data.sodium / divisor)
                     db.commit()
                     db.refresh(food_item)

        if not food_item:
            if data.food_name:
                # Calculate per-unit values if provided (User sends Total, Cache stores Per Unit)
                divisor = (data.quantity * data.serving_size) if (data.quantity * data.serving_size) > 0 else 1.0

                # Visibility logic: Defaults to False if flag is missing/0 for MANUAL entry
                is_visible = bool(data.save_food) if data.save_food is not None else False

                food_item = models.NutritionCache(
                    barcode=data.barcode,
                    food_name=data.food_name,
                    calories=(data.calories or 0) / divisor,
                    protein=(data.protein or 0) / divisor,
                    fat=(data.fat or 0) / divisor,
                    carbs=(data.carbs or 0) / divisor,
                    fiber=(data.fiber or 0) / divisor,
                    sodium=(data.sodium or 0) / divisor,
                    source="MANUAL",
                    is_user_visible=is_visible
                )
                db.add(food_item)
                db.commit()
                db.refresh(food_item)
            else:
                return None, "Food not found"

        ts = data.timestamp
        if not ts:
            ts = datetime.now(timezone.utc)
        elif ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        item_log = models.FoodItemLog(
            user_id=user.user_id, meal_id=data.meal_id, food_id=food_item.food_id,
            serving_size=data.serving_size, quantity=data.quantity,
            planned_quantity=data.planned_quantity,
            timestamp=ts
        )
        db.add(item_log)
        local_date = get_user_local_date(user, ts)
        daily_log = db.query(models.DailyLog).filter(models.DailyLog.user_id == user.user_id, models.DailyLog.date == local_date).first()
        if not daily_log:
            daily_log = models.DailyLog(user_id=user.user_id, date=local_date, total_calories_burned=0, total_calories_consumed=0)
            db.add(daily_log)

        # Only add to DailyLog if explicitly eaten (quantity > 0)
        # Planned items (quantity=0) do not count towards daily totals in DB
        if data.quantity > 0:
            total_cals = food_item.calories * data.serving_size * data.quantity
            daily_log.total_calories_consumed += total_cals

        db.commit()
        return item_log, None

    def delete_exercise_log(self, db: Session, log_id: int, user_id: int):
        log = db.query(models.ExerciseLog).filter(models.ExerciseLog.exercise_id == log_id, models.ExerciseLog.user_id == user_id).first()
        if not log: return False

        # Deduct from DailyLog
        local_date = get_user_local_date(log.user, log.timestamp)
        daily_log = db.query(models.DailyLog).filter(models.DailyLog.user_id == user_id, models.DailyLog.date == local_date).first()
        if daily_log:
            daily_log.total_calories_burned -= log.calories_burned
            if daily_log.total_calories_burned < 0: daily_log.total_calories_burned = 0

        db.delete(log)
        db.commit()
        return True

    def update_exercise_log(self, db: Session, log_id: int, user_id: int, updates: schemas.LogUpdate):
        log = db.query(models.ExerciseLog).filter(models.ExerciseLog.exercise_id == log_id, models.ExerciseLog.user_id == user_id).first()
        if not log: return None

        # We must handle DailyLog updates.
        # Strategy: Revert old values from old date's log, Apply new values to new date's log.
        old_cals = log.calories_burned
        old_date = get_user_local_date(log.user, log.timestamp)

        # Apply updates to object in memory
        if updates.timestamp: log.timestamp = updates.timestamp
        if updates.activity_type: log.activity_type = updates.activity_type
        if updates.duration_minutes is not None: log.duration_minutes = updates.duration_minutes

        # Recalculate calories if needed?
        # If user updates cals explicit:
        if updates.calories_burned is not None:
             log.calories_burned = updates.calories_burned
        # If user updates duration but not cals, maybe recalculate?
        # For simplicity, if they update duration we will just recalculate if they don't provide cals.
        # But here 'updates.calories_burned' might be None.
        # Let's assume frontend passes cals if they want to override.
        # If just duration changed, we might want to recalculate using MET?
        # The prompt says "edit those entries".
        # Let's trust the input. If they change duration, frontend should ideally recalc cals or send 0?
        # Let's stick to direct field updates for now unless cals is missing and duration changed.
        elif updates.duration_minutes is not None and log.activity_type:
             # Try calc
             met_calc = METCalculator()
             log.calories_burned = met_calc.calculate_calories(db, log.user, log.activity_type, log.duration_minutes)

        new_cals = log.calories_burned
        new_date = get_user_local_date(log.user, log.timestamp)

        # Update DB for DailyLogs
        # 1. Revert Old
        old_daily = db.query(models.DailyLog).filter(models.DailyLog.user_id == user_id, models.DailyLog.date == old_date).first()
        if old_daily:
            old_daily.total_calories_burned -= old_cals
            if old_daily.total_calories_burned < 0: old_daily.total_calories_burned = 0

        # 2. Apply New
        new_daily = db.query(models.DailyLog).filter(models.DailyLog.user_id == user_id, models.DailyLog.date == new_date).first()
        if not new_daily:
            new_daily = models.DailyLog(user_id=user_id, date=new_date, total_calories_burned=0, total_calories_consumed=0)
            db.add(new_daily)
        new_daily.total_calories_burned += new_cals

        db.commit()
        db.refresh(log)
        return log

    def delete_food_log(self, db: Session, log_id: int, user_id: int):
        log = db.query(models.FoodItemLog).filter(models.FoodItemLog.item_log_id == log_id, models.FoodItemLog.user_id == user_id).first()
        if not log: return False

        # Deduct from DailyLog
        # Need to know total calories of this item
        # log has nutrition_info rel
        # Only deduct if it was eaten (quantity > 0)
        cals = 0.0
        if log.quantity > 0:
            cals = log.nutrition_info.calories * log.serving_size * log.quantity

        local_date = get_user_local_date(log.user, log.timestamp)
        daily_log = db.query(models.DailyLog).filter(models.DailyLog.user_id == user_id, models.DailyLog.date == local_date).first()
        if daily_log:
            daily_log.total_calories_consumed -= cals
            if daily_log.total_calories_consumed < 0: daily_log.total_calories_consumed = 0

        db.delete(log)
        db.commit()
        return True

    def update_food_log(self, db: Session, log_id: int, user_id: int, updates: schemas.LogUpdate):
        log = db.query(models.FoodItemLog).filter(models.FoodItemLog.item_log_id == log_id, models.FoodItemLog.user_id == user_id).first()
        if not log: return None

        # Old values (only count towards daily log if quantity > 0)
        old_cals = 0.0
        if log.quantity > 0:
            old_cals = log.nutrition_info.calories * log.serving_size * log.quantity

        old_date = get_user_local_date(log.user, log.timestamp)

        # Updates
        if updates.timestamp: log.timestamp = updates.timestamp
        if updates.quantity is not None: log.quantity = updates.quantity
        if updates.planned_quantity is not None: log.planned_quantity = updates.planned_quantity
        if updates.serving_size is not None: log.serving_size = updates.serving_size
        if updates.meal_id: log.meal_id = updates.meal_id

        # New values (only count towards daily log if quantity > 0)
        new_cals = 0.0
        if log.quantity > 0:
            new_cals = log.nutrition_info.calories * log.serving_size * log.quantity

        new_date = get_user_local_date(log.user, log.timestamp)

        # Update DailyLogs
        old_daily = db.query(models.DailyLog).filter(models.DailyLog.user_id == user_id, models.DailyLog.date == old_date).first()
        if old_daily:
            old_daily.total_calories_consumed -= old_cals
            if old_daily.total_calories_consumed < 0: old_daily.total_calories_consumed = 0

        new_daily = db.query(models.DailyLog).filter(models.DailyLog.user_id == user_id, models.DailyLog.date == new_date).first()
        if not new_daily:
            new_daily = models.DailyLog(user_id=user_id, date=new_date, total_calories_burned=0, total_calories_consumed=0)
            db.add(new_daily)
        new_daily.total_calories_consumed += new_cals

        db.commit()
        db.refresh(log)
        return log

    def log_weight(self, db: Session, user: models.User, weight_kg: float, timestamp: datetime = None):
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Ensure timestamp has timezone
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        # Update User Profile
        user.weight_kg = weight_kg

        # Log History
        log = models.WeightLog(
            user_id=user.user_id,
            weight_kg=weight_kg,
            timestamp=timestamp
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def get_weight_change(self, db: Session, user: models.User, days: int = 30) -> float:
        """
        Calculates weight change over the last N days.
        Returns: current_weight - weight_N_days_ago.
        Positive = Gained, Negative = Lost.
        """
        if not user.weight_kg:
            return 0.0

        # Current is simply the user's current profile weight
        current_weight = user.weight_kg

        # Target date: N days ago
        now = datetime.now(timezone.utc)
        target_date = now - timedelta(days=days)

        # Find the weight log closest to target_date (before or at target_date)
        # We want the most recent log that is <= target_date
        past_log = db.query(models.WeightLog).filter(
            models.WeightLog.user_id == user.user_id,
            models.WeightLog.timestamp <= target_date
        ).order_by(models.WeightLog.timestamp.desc()).first()

        if not past_log:
            # If no log found before 30 days ago, try to find the oldest log available
            # This handles cases where user started < 30 days ago.
            past_log = db.query(models.WeightLog).filter(
                models.WeightLog.user_id == user.user_id
            ).order_by(models.WeightLog.timestamp.asc()).first()

        if past_log:
            return current_weight - past_log.weight_kg

        return 0.0

    def get_exercise_streak(self, db: Session, user: models.User) -> int:
        """
        Calculates consecutive days with at least one exercise log.
        """
        try:
            user_tz = zoneinfo.ZoneInfo(user.timezone) if user.timezone else timezone.utc
        except Exception:
            user_tz = timezone.utc

        # Get all unique dates with exercise
        # We fetch timestamp and convert to local date in python to avoid DB dialect issues
        logs = db.query(models.ExerciseLog.timestamp).filter(
            models.ExerciseLog.user_id == user.user_id
        ).order_by(models.ExerciseLog.timestamp.desc()).all()

        if not logs:
            return 0

        unique_dates = set()
        for log in logs:
            ts = log.timestamp
            if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
            local_date = ts.astimezone(user_tz).date()
            unique_dates.add(local_date)

        sorted_dates = sorted(list(unique_dates), reverse=True)

        if not sorted_dates:
            return 0

        today = datetime.now(user_tz).date()
        yesterday = today - timedelta(days=1)

        # Streak must include today or yesterday to be active
        if sorted_dates[0] < yesterday:
            return 0

        streak = 0
        current = today

        # If the latest exercise was today, start counting from today.
        # If the latest was yesterday, start counting from yesterday.
        # (Already checked that latest >= yesterday)
        if sorted_dates[0] == today:
            streak = 1
            current = yesterday
        elif sorted_dates[0] == yesterday:
            streak = 1
            current = yesterday - timedelta(days=1)

        # Check previous days
        # We need to check if 'current' exists in sorted_dates
        # But iterating through sorted_dates is more efficient

        # Pointer for sorted_dates. We already consumed index 0.
        idx = 1
        while idx < len(sorted_dates):
            if sorted_dates[idx] == current:
                streak += 1
                current -= timedelta(days=1)
                idx += 1
            else:
                break

        return streak

    def get_daily_summary_data(self, db: Session, current_user: models.User, target_date: date):
        # 1. Daily Log (Calories In/Out)
        daily = db.query(models.DailyLog).filter(
            models.DailyLog.user_id == current_user.user_id,
            models.DailyLog.date == target_date
        ).first()

        calories_consumed = daily.total_calories_consumed if daily else 0
        calories_burned = daily.total_calories_burned if daily else 0

        # Determine UTC range for the User's Local Day
        try:
            user_tz = zoneinfo.ZoneInfo(current_user.timezone) if current_user.timezone else timezone.utc
        except Exception:
            user_tz = timezone.utc

        # Local day start/end
        local_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=user_tz)
        local_end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=user_tz)

        # Convert to UTC for DB Query
        utc_start = local_start.astimezone(timezone.utc)
        utc_end = local_end.astimezone(timezone.utc)

        # 2. Latest BP
        bp = db.query(models.BloodPressure).filter(
            models.BloodPressure.user_id == current_user.user_id,
            models.BloodPressure.timestamp >= utc_start,
            models.BloodPressure.timestamp <= utc_end
        ).order_by(models.BloodPressure.timestamp.desc()).first()

        bp_str = f"{bp.systolic}/{bp.diastolic}" if bp else "Not Logged"

        # 3. Macro Calculation
        food_logs = db.query(models.FoodItemLog).join(models.NutritionCache).filter(
            models.FoodItemLog.user_id == current_user.user_id,
            models.FoodItemLog.timestamp >= utc_start,
            models.FoodItemLog.timestamp <= utc_end
        ).all()

        macros = {
            "protein": 0, "fat": 0, "carbs": 0, "fiber": 0, "sodium": 0,
            "cholesterol": 0, "total_sugars": 0, "added_sugars": 0,
            "vitamin_d": 0, "calcium": 0, "iron": 0, "potassium": 0
        }
        food_list = []
        for log in food_logs:
            multiplier = log.serving_size * log.quantity
            macros["protein"] += (log.nutrition_info.protein or 0) * multiplier
            macros["fat"] += (log.nutrition_info.fat or 0) * multiplier
            macros["carbs"] += (log.nutrition_info.carbs or 0) * multiplier
            macros["fiber"] += (log.nutrition_info.fiber or 0) * multiplier
            macros["sodium"] += (log.nutrition_info.sodium or 0) * multiplier

            # Extended & Micros
            macros["cholesterol"] += (log.nutrition_info.cholesterol or 0) * multiplier
            macros["total_sugars"] += (log.nutrition_info.total_sugars or 0) * multiplier
            macros["added_sugars"] += (log.nutrition_info.added_sugars or 0) * multiplier
            macros["vitamin_d"] += (log.nutrition_info.vitamin_d or 0) * multiplier
            macros["calcium"] += (log.nutrition_info.calcium or 0) * multiplier
            macros["iron"] += (log.nutrition_info.iron or 0) * multiplier
            macros["potassium"] += (log.nutrition_info.potassium or 0) * multiplier

            ts = log.timestamp
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            # Use planned quantity for display calculation if not eaten yet
            display_mult = log.quantity if log.quantity > 0 else log.planned_quantity

            food_list.append({
                "log_id": log.item_log_id,
                "food_id": log.food_id,
                "name": log.nutrition_info.food_name,
                "calories": (log.nutrition_info.calories or 0) * display_mult * log.serving_size,
                "protein": (log.nutrition_info.protein or 0) * display_mult * log.serving_size,
                "fat": (log.nutrition_info.fat or 0) * display_mult * log.serving_size,
                "carbs": (log.nutrition_info.carbs or 0) * display_mult * log.serving_size,
                "fiber": (log.nutrition_info.fiber or 0) * display_mult * log.serving_size,
                "sodium": (log.nutrition_info.sodium or 0) * display_mult * log.serving_size,
                "meal": log.meal_id,
                "serving_size": log.serving_size,
                "quantity": log.quantity,
                "planned_quantity": log.planned_quantity,
                "unit": log.nutrition_info.serving_size_unit,
                "timestamp": ts
            })

        # Fetch Exercises
        exercises_list = []
        daily_exercises = db.query(models.ExerciseLog).filter(
            models.ExerciseLog.user_id == current_user.user_id,
            models.ExerciseLog.timestamp >= utc_start,
            models.ExerciseLog.timestamp <= utc_end
        ).order_by(models.ExerciseLog.timestamp.desc()).all()

        for ex in daily_exercises:
            ts = ex.timestamp
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            exercises_list.append({
                "log_id": ex.exercise_id,
                "activity": ex.activity_type,
                "duration": ex.duration_minutes,
                "calories": ex.calories_burned,
                "timestamp": ts
            })

        # Weight Change & Streak
        weight_change = self.get_weight_change(db, current_user, days=30)
        exercise_streak = self.get_exercise_streak(db, current_user)

        return {
            "blood_pressure": bp_str,
            "calories_consumed": calories_consumed,
            "calories_burned": calories_burned,
            "macros": macros,
            "food_logs": food_list,
            "exercises": exercises_list,
            "weight_change_30d": weight_change,
            "exercise_streak": exercise_streak
        }

    def calculate_compliance_report(self, db: Session, user: models.User):
        try:
            user_tz = zoneinfo.ZoneInfo(user.timezone) if user.timezone else timezone.utc
        except Exception:
            user_tz = timezone.utc

        # [FIXED INDENTATION HERE]
        end_date = get_user_local_date(user, datetime.now(timezone.utc)) - timedelta(days=1)
        start_date = end_date - timedelta(days=29)

        # Get active medications
        meds = db.query(models.Medication).filter(models.Medication.user_id == user.user_id).all()
        if not meds:
            return {"compliance_percentage": 0, "missed_doses": 0, "taken_doses": 0, "total_scheduled": 0, "medications": []}
            
        start_dt = datetime.combine(start_date, time.min).replace(tzinfo=user_tz)
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min).replace(tzinfo=user_tz)
        
        logs = db.query(models.MedDoseLog).filter(
            models.MedDoseLog.user_id == user.user_id,
            models.MedDoseLog.timestamp_taken >= start_dt,
            models.MedDoseLog.timestamp_taken < end_dt
        ).all()

        windows = [
            ("morning", user.window_morning_start or time(6, 0)),
            ("afternoon", user.window_afternoon_start or time(12, 0)),
            ("evening", user.window_evening_start or time(17, 0)),
            ("bedtime", user.window_bedtime_start or time(21, 0))
        ]
        windows.sort(key=lambda x: x[1])

        def get_window_and_date(ts: datetime):
            if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
            ts_local = ts.astimezone(user_tz)
            t = ts_local.time()
            d = ts_local.date()
            matched_window = None
            for w_name, w_start in windows:
                if t >= w_start:
                    matched_window = w_name
                else:
                    break
            if matched_window:
                return matched_window, d
            else:
                return windows[-1][0], d - timedelta(days=1)

        taken_set = set()
        for log in logs:
            if log.dose_window:
                w_name = log.dose_window
                # Date logic: If explicit bedtime dose is taken early morning (before morning window),
                # attribute it to previous day.
                # Note: get_window_and_date logic handles this for inferred windows.
                # We need similar logic here for explicit windows.
                if log.timestamp_taken.tzinfo is None:
                     ts = log.timestamp_taken.replace(tzinfo=timezone.utc)
                else:
                     ts = log.timestamp_taken
                ts_local = ts.astimezone(user_tz)
                w_date = ts_local.date()

                morning_start = windows[0][1] # First window is morning

                if w_name == "bedtime" and ts_local.time() < morning_start:
                     w_date -= timedelta(days=1)
            else:
                w_name, w_date = get_window_and_date(log.timestamp_taken)

            if start_date <= w_date <= end_date:
                taken_set.add((log.med_id, w_name, w_date))

        total_expected = 0
        total_taken = 0
        med_stats = {med.med_id: {"name": med.name, "taken": 0, "expected": 0} for med in meds}

        current_d = start_date
        while current_d <= end_date:
            for med in meds:
                # Check active range
                # If start_date is set, ignore if current_d < start_date
                # Note: start_date is inclusive
                if med.start_date and current_d < med.start_date:
                    continue
                # If end_date is set, ignore if current_d > end_date
                # Note: end_date is inclusive
                if med.end_date and current_d > med.end_date:
                    continue

                schedule = []
                if med.schedule_morning: schedule.append("morning")
                if med.schedule_afternoon: schedule.append("afternoon")
                if med.schedule_evening: schedule.append("evening")
                if med.schedule_bedtime: schedule.append("bedtime")
                for w in schedule:
                    total_expected += 1
                    med_stats[med.med_id]["expected"] += 1
                    if (med.med_id, w, current_d) in taken_set:
                        total_taken += 1
                        med_stats[med.med_id]["taken"] += 1
            current_d += timedelta(days=1)

        percentage = (total_taken / total_expected * 100) if total_expected > 0 else 0.0
        missed = total_expected - total_taken
        medications_list = []
        for mid, stats in med_stats.items():
            exp = stats["expected"]
            tak = stats["taken"]
            pct = (tak / exp * 100) if exp > 0 else 100.0
            med = next((m for m in meds if m.med_id == mid), None)
            schedule_str = []
            if med:
                if med.schedule_morning: schedule_str.append("M")
                if med.schedule_afternoon: schedule_str.append("A")
                if med.schedule_evening: schedule_str.append("E")
                if med.schedule_bedtime: schedule_str.append("B")
            medications_list.append({
                "name": stats["name"], "compliance_percentage": round(pct, 1),
                "taken": tak, "expected": exp, "missed": exp - tak, "schedule": ", ".join(schedule_str)
            })
        return {
            "compliance_percentage": round(percentage, 1), "missed_doses": missed,
            "taken_doses": total_taken, "total_scheduled": total_expected,
            "medications": medications_list
        }

class BackupService:
    CONFIG_KEY = "backup_encryption_key"
    BACKUP_DIR = "backups"
    DB_FILE = "health_app.db"
    def _derive_fernet_key(self, passphrase: str) -> bytes:
        digest = hashlib.sha256(passphrase.encode()).digest()
        return base64.urlsafe_b64encode(digest)
    def set_key(self, db: Session, key_str: str):
        config = db.query(models.SystemConfig).filter(models.SystemConfig.key == self.CONFIG_KEY).first()
        if not config:
            config = models.SystemConfig(key=self.CONFIG_KEY, value=key_str)
            db.add(config)
        else:
            config.value = key_str
        db.commit()
    def get_key(self, db: Session):
        config = db.query(models.SystemConfig).filter(models.SystemConfig.key == self.CONFIG_KEY).first()
        return config.value if config else None
    def create_backup(self, db: Session) -> str:
        key_str = self.get_key(db)
        if not key_str: raise ValueError("Encryption key not set")
        if not os.path.exists(self.BACKUP_DIR): os.makedirs(self.BACKUP_DIR)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}.enc"
        filepath = os.path.join(self.BACKUP_DIR, filename)
        fernet = Fernet(self._derive_fernet_key(key_str))
        with open(self.DB_FILE, "rb") as f:
            data = f.read()
        encrypted_data = fernet.encrypt(data)
        with open(filepath, "wb") as f:
            f.write(encrypted_data)
        return filename
    def restore_backup(self, db: Session, file_bytes: bytes):
        key_str = self.get_key(db)
        if not key_str: raise ValueError("Encryption key not set")
        fernet = Fernet(self._derive_fernet_key(key_str))
        try:
            decrypted_data = fernet.decrypt(file_bytes)
        except Exception:
            raise ValueError("Invalid Key or Corrupt Backup")
        database.dispose_engine()
        backup_path = self.DB_FILE + ".bak"
        if os.path.exists(self.DB_FILE):
            shutil.move(self.DB_FILE, backup_path)
        with open(self.DB_FILE, "wb") as f:
            f.write(decrypted_data)
        return True
    def get_latest_backup(self):
        if not os.path.exists(self.BACKUP_DIR): return None
        files = [os.path.join(self.BACKUP_DIR, f) for f in os.listdir(self.BACKUP_DIR) if f.endswith(".enc")]
        if not files: return None
        return max(files, key=os.path.getctime)

class GeminiService:
    def ask_nutrition_advice(self, summary_data: dict, staples_list: List[models.NutritionCache]) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Gemini API Key not configured. Please set GEMINI_API_KEY environment variable."

        try:
            client = genai.Client(api_key=api_key)

            # Prepare Staples String
            staples_str = ", ".join([f"{s.food_name}" for s in staples_list])
            if not staples_str:
                staples_str = "No specific staples listed."

            # Prepare Summary String
            # We filter food_logs to only relevant fields for prompt to save tokens/clutter
            eaten_list = [f"{f['name']} ({f['calories']} kcal, {f['meal']})" for f in summary_data.get('food_logs', []) if f['quantity'] > 0]
            eaten_str = "\n".join(eaten_list) if eaten_list else "Nothing eaten yet."

            prompt = f"""
            You are a helpful nutrition assistant.

            Here is my daily nutrition summary so far:
            Calories Consumed: {summary_data.get('calories_consumed')}
            Macros Consumed: {summary_data.get('macros')}

            Foods eaten today:
            {eaten_str}

            Here is a list of staple foods I have available at home:
            {staples_str}

            Based on what I have eaten and what I have available, what do you recommend I eat for my next meal or snack to balance my nutrition for the day?
            Please give specific suggestions from my staples list if possible, or general advice if staples aren't sufficient.
            Keep the response concise, friendly, and actionable. Format nicely with markdown if possible.
            """

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error communicating with Gemini (SDK v1): {str(e)}"
