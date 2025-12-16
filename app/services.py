import requests
from sqlalchemy.orm import Session
from app import models
from app import schemas
from datetime import datetime, date, timedelta, time

class OpenFoodFactsService:
    BASE_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

    def get_product(self, barcode: str, db: Session):
        # 1. Check local cache
        cached = db.query(models.NutritionCache).filter(models.NutritionCache.barcode == barcode).first()
        if cached:
            return cached

        # 2. Call External API
        response = requests.get(self.BASE_URL.format(barcode=barcode))
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 1:
                product = data["product"]
                nutriments = product.get("nutriments", {})

                # Extract data
                food_name = product.get("product_name", "Unknown")
                calories = nutriments.get("energy-kcal_100g", 0)
                protein = nutriments.get("proteins_100g", 0)
                fat = nutriments.get("fat_100g", 0)
                carbs = nutriments.get("carbohydrates_100g", 0)
                fiber = nutriments.get("fiber_100g", 0)

                # Write to Cache
                new_cache = models.NutritionCache(
                    barcode=barcode,
                    food_name=food_name,
                    calories=float(calories) if calories else 0.0,
                    protein=float(protein) if protein else 0.0,
                    fat=float(fat) if fat else 0.0,
                    carbs=float(carbs) if carbs else 0.0,
                    fiber=float(fiber) if fiber else 0.0,
                    source="OFF"
                )
                db.add(new_cache)
                db.commit()
                db.refresh(new_cache)
                return new_cache

        return None

class METCalculator:
    def calculate_calories(self, db: Session, user: models.User, activity_type: str, duration_minutes: float):
        # Formula: Total Calories = (MET Value * Weight in kg * 3.5 / 200) * Duration in minutes

        # 1. Lookup MET value
        # Basic mapping if DB is empty or miss
        default_mets = {
            "running": 9.8,
            "walking": 3.8,
            "cycling": 7.5,
            "swimming": 8.0,
            "yoga": 2.5
        }

        met_entry = db.query(models.METLookup).filter(models.METLookup.activity_name == activity_type.lower()).first()
        met_value = met_entry.met_value if met_entry else default_mets.get(activity_type.lower(), 1.0) # Default to 1 (resting)

        calories = (met_value * user.weight_kg * 3.5 / 200) * duration_minutes
        return calories

class MedicationService:
    def log_dose(self, db: Session, user_id: int, med_name: str, timestamp_taken: datetime = None):
        if not timestamp_taken:
            timestamp_taken = datetime.utcnow()

        med = db.query(models.Medication).filter(
            models.Medication.user_id == user_id,
            models.Medication.name == med_name
        ).first()

        if not med:
            return None, "Medication not found"

        # Decrement Inventory
        if med.current_inventory > 0:
            med.current_inventory -= 1

        # Calculate Drift (Simplified - assuming frequency string contains info or we just log 0 for now)
        # Plan says "compare timestamp_taken to the scheduled time".
        # We don't have a "Scheduled Time" field in Medication, only "frequency".
        # Assuming we just log 0 drift for now as scheduling logic is complex (crontab style?).
        drift = 0.0

        # Log Dose
        dose_log = models.MedDoseLog(
            user_id=user_id,
            med_id=med.med_id,
            timestamp_taken=timestamp_taken,
            target_time_drift=drift
        )
        db.add(dose_log)

        # Check Refills
        alert = None
        days_remaining = med.current_inventory / med.daily_doses if med.daily_doses > 0 else 999
        if days_remaining <= 7 or med.refills_remaining <= 1:
            alert = f"Refill needed for {med.name}. Days remaining: {days_remaining:.1f}, Refills: {med.refills_remaining}"

        db.commit()
        return dose_log, alert

class HealthLogService:
    def log_bp(self, db: Session, user_id: int, data: schemas.BPPayload):
        bp = models.BloodPressure(
            user_id=user_id,
            systolic=data.systolic,
            diastolic=data.diastolic,
            pulse=data.pulse,
            location=data.location,
            stress_level=data.stress_level,
            meds_taken_before=data.meds_taken_before
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

        # 1. Save detailed log
        exercise_log = models.ExerciseLog(
            user_id=user.user_id,
            activity_type=data.activity_type,
            duration_minutes=data.duration_minutes,
            calories_burned=calories
        )
        db.add(exercise_log)

        # 2. Update Daily Log (Summary)
        today = date.today()
        daily_log = db.query(models.DailyLog).filter(models.DailyLog.user_id == user.user_id, models.DailyLog.date == today).first()
        if not daily_log:
            daily_log = models.DailyLog(user_id=user.user_id, date=today, total_calories_burned=0, total_calories_consumed=0)
            db.add(daily_log)

        daily_log.total_calories_burned += calories
        db.commit()
        return daily_log

    def log_food(self, db: Session, user: models.User, data: schemas.FoodLogPayload):
        off_service = OpenFoodFactsService()

        food_item = None
        if data.barcode:
            food_item = off_service.get_product(data.barcode, db)

        # If not found or no barcode, handle manual or fallback
        # Ideally if no barcode, we look up by name in cache or fail to manual
        if not food_item and data.food_name:
             # Try to find by name in cache
             food_item = db.query(models.NutritionCache).filter(models.NutritionCache.food_name == data.food_name).first()

        if not food_item:
            # Plan says "API Fail (404): Flag for user manual entry".
            # For automation, we might need to create a placeholder or error out.
            # Let's create a placeholder Manual entry if it doesn't exist
            if data.food_name:
                 food_item = models.NutritionCache(
                    barcode=data.barcode, # might be None
                    food_name=data.food_name,
                    calories=0, # Unknown
                    protein=0,
                    fat=0,
                    carbs=0,
                    fiber=0,
                    source="MANUAL"
                 )
                 db.add(food_item)
                 db.commit()
                 db.refresh(food_item)
            else:
                return None, "Food not found and no name provided"

        # Log Item
        item_log = models.FoodItemLog(
            user_id=user.user_id,
            meal_id=data.meal_id,
            food_id=food_item.food_id,
            serving_size=data.serving_size,
            quantity=data.quantity
        )
        db.add(item_log)

        # Update Daily Log
        today = date.today()
        daily_log = db.query(models.DailyLog).filter(models.DailyLog.user_id == user.user_id, models.DailyLog.date == today).first()
        if not daily_log:
            daily_log = models.DailyLog(user_id=user.user_id, date=today, total_calories_burned=0, total_calories_consumed=0)
            db.add(daily_log)

        total_cals = food_item.calories * data.serving_size * data.quantity
        daily_log.total_calories_consumed += total_cals

        db.commit()
        return item_log, None

    def calculate_compliance_report(self, db: Session, user: models.User):
        # Time range: Last 30 days excluding today
        today = date.today()
        start_date = today - timedelta(days=30)
        end_date = today - timedelta(days=1)

        # Get active medications
        meds = db.query(models.Medication).filter(models.Medication.user_id == user.user_id).all()
        if not meds:
            return {"compliance_percentage": 0, "missed_doses": 0, "taken_doses": 0, "total_scheduled": 0}

        # Get all logs for this period
        logs = db.query(models.MedDoseLog).filter(
            models.MedDoseLog.user_id == user.user_id,
            models.MedDoseLog.timestamp_taken >= datetime.combine(start_date, time.min),
            models.MedDoseLog.timestamp_taken <= datetime.combine(end_date, time.max)
        ).all()

        # Helper to map timestamp to (Window, LogicalDate)
        # Windows: Morning(M), Afternoon(A), Evening(E), Bedtime(B)
        # B can span to next day.
        # Logic: Find the latest window start time that is <= timestamp.time()
        # If timestamp < M_start (and M is earliest), it wraps to previous day's LAST window (Bedtime).

        # Sort windows by time
        windows = [
            ("morning", user.window_morning_start or time(6, 0)),
            ("afternoon", user.window_afternoon_start or time(12, 0)),
            ("evening", user.window_evening_start or time(17, 0)),
            ("bedtime", user.window_bedtime_start or time(21, 0))
        ]
        # Sort based on time object
        windows.sort(key=lambda x: x[1])

        def get_window_and_date(ts: datetime):
            t = ts.time()
            d = ts.date()

            # Find the slot
            matched_window = None

            # Check normal order
            # If t is 08:00 and windows are 06, 12, 17, 21. 08 >= 06. Matched=Morning.
            # If t is 23:00. 23 >= 21. Matched=Bedtime.
            # If t is 01:00. < 06. Loop finishes. Matched=None?

            for w_name, w_start in windows:
                if t >= w_start:
                    matched_window = w_name
                else:
                    break

            if matched_window:
                return matched_window, d
            else:
                # If earlier than the first window, it belongs to the LAST window of the PREVIOUS day.
                # Assuming the last window in sorted list is the one that wraps (usually Bedtime).
                return windows[-1][0], d - timedelta(days=1)

        # Build a set of (med_id, window, date) for taken doses
        taken_set = set()
        for log in logs:
            w_name, w_date = get_window_and_date(log.timestamp_taken)
            if start_date <= w_date <= end_date:
                taken_set.add((log.med_id, w_name, w_date))

        # Calculate Expected Doses
        total_expected = 0
        total_taken = 0

        current_d = start_date
        while current_d <= end_date:
            for med in meds:
                # Check scheduled windows
                schedule = []
                if med.schedule_morning: schedule.append("morning")
                if med.schedule_afternoon: schedule.append("afternoon")
                if med.schedule_evening: schedule.append("evening")
                if med.schedule_bedtime: schedule.append("bedtime")

                for w in schedule:
                    total_expected += 1
                    if (med.med_id, w, current_d) in taken_set:
                        total_taken += 1

            current_d += timedelta(days=1)

        percentage = (total_taken / total_expected * 100) if total_expected > 0 else 0.0
        missed = total_expected - total_taken

        return {
            "compliance_percentage": round(percentage, 1),
            "missed_doses": missed,
            "taken_doses": total_taken,
            "total_scheduled": total_expected
        }
