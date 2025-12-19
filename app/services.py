
import requests
import os
import shutil
from sqlalchemy.orm import Session
from app import models, schemas, database
from datetime import datetime, date, timedelta, time
from cryptography.fernet import Fernet
import base64
import hashlib

class OpenFoodFactsService:
    BASE_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

    def get_product(self, barcode: str, db: Session):
        cached = db.query(models.NutritionCache).filter(models.NutritionCache.barcode == barcode).first()
        if cached:
            return cached

        response = requests.get(self.BASE_URL.format(barcode=barcode))
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 1 or data.get("product"):
                product = data["product"]
                nutriments = product.get("nutriments", {})
                food_name = product.get("product_name", "Unknown")
                def get_nutriment(key):
                    val = nutriments.get(key)
                    if val is None: return 0.0
                    try: return float(val)
                    except (ValueError, TypeError): return 0.0
                calories = get_nutriment("energy-kcal_100g")
                if calories == 0:
                    kj = get_nutriment("energy-kj_100g")
                    if kj > 0: calories = kj / 4.184
                protein = get_nutriment("proteins_100g")
                fat = get_nutriment("fat_100g")
                carbs = get_nutriment("carbohydrates_100g")
                fiber = get_nutriment("fiber_100g")
                new_cache = models.NutritionCache(
                    barcode=barcode, food_name=food_name, calories=calories,
                    protein=protein, fat=fat, carbs=carbs, fiber=fiber, source="OFF"
                )
                db.add(new_cache)
                db.commit()
                db.refresh(new_cache)
                return new_cache
        return None

class METCalculator:
    def calculate_calories(self, db: Session, user: models.User, activity_type: str, duration_minutes: float):
        default_mets = {"running": 9.8, "walking": 3.8, "cycling": 7.5, "swimming": 8.0, "yoga": 2.5}
        met_entry = db.query(models.METLookup).filter(models.METLookup.activity_name == activity_type.lower()).first()
        met_value = met_entry.met_value if met_entry else default_mets.get(activity_type.lower(), 1.0)
        return (met_value * user.weight_kg * 3.5 / 200) * duration_minutes

from datetime import timezone
import zoneinfo

def get_user_local_date(user: models.User, utc_dt: datetime) -> date:
    if not utc_dt: utc_dt = datetime.now(timezone.utc)
    if utc_dt.tzinfo is None: utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    try:
        user_tz = zoneinfo.ZoneInfo(user.timezone) if user.timezone else timezone.utc
    except Exception:
        user_tz = timezone.utc
    return utc_dt.astimezone(user_tz).date()

class MedicationService:
    def log_dose(self, db: Session, user_id: int, med_name: str, timestamp_taken: datetime = None):
        if not timestamp_taken: timestamp_taken = datetime.now(timezone.utc)
        med = db.query(models.Medication).filter(
            models.Medication.user_id == user_id, models.Medication.name == med_name
        ).first()
        if not med: return None, "Medication not found"
        if med.current_inventory > 0: med.current_inventory -= 1
        dose_log = models.MedDoseLog(
            user_id=user_id, med_id=med.med_id,
            timestamp_taken=timestamp_taken, target_time_drift=0.0
        )
        db.add(dose_log)
        alert = None
        days_remaining = med.current_inventory / med.daily_doses if med.daily_doses > 0 else 999
        if days_remaining <= 7 or med.refills_remaining <= 1:
            alert = f"Refill needed for {med.name}. Days remaining: {days_remaining:.1f}, Refills: {med.refills_remaining}"
        db.commit()
        return dose_log, alert

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
        return daily_log

    def log_food(self, db: Session, user: models.User, data: schemas.FoodLogPayload):
        off_service = OpenFoodFactsService()
        food_item = None
        if data.barcode: food_item = off_service.get_product(data.barcode, db)
        if not food_item and data.food_name:
            food_item = db.query(models.NutritionCache).filter(models.NutritionCache.food_name == data.food_name).first()
        if not food_item:
            if data.food_name:
                food_item = models.NutritionCache(
                    barcode=data.barcode, food_name=data.food_name, calories=0,
                    protein=0, fat=0, carbs=0, fiber=0, source="MANUAL"
                )
                db.add(food_item)
                db.commit()
                db.refresh(food_item)
            else:
                return None, "Food not found"
        item_log = models.FoodItemLog(
            user_id=user.user_id, meal_id=data.meal_id, food_id=food_item.food_id,
            serving_size=data.serving_size, quantity=data.quantity
        )
        db.add(item_log)
        local_date = get_user_local_date(user, datetime.now(timezone.utc))
        daily_log = db.query(models.DailyLog).filter(models.DailyLog.user_id == user.user_id, models.DailyLog.date == local_date).first()
        if not daily_log:
            daily_log = models.DailyLog(user_id=user.user_id, date=local_date, total_calories_burned=0, total_calories_consumed=0)
            db.add(daily_log)
        total_cals = food_item.calories * data.serving_size * data.quantity
        daily_log.total_calories_consumed += total_cals
        db.commit()
        return item_log, None

    def calculate_compliance_report(self, db: Session, user: models.User):
        end_date = get_user_local_date(user, datetime.now(timezone.utc)) - timedelta(days=1)
        start_date = end_date - timedelta(days=29)
        meds = db.query(models.Medication).filter(models.Medication.user_id == user.user_id).all()
        if not meds:
            return {"compliance_percentage": 0, "missed_doses": 0, "taken_doses": 0, "total_scheduled": 0, "medications": []}

        import zoneinfo
        try:
            user_tz = zoneinfo.ZoneInfo(user.timezone) if user.timezone else timezone.utc
        except Exception:
            user_tz = timezone.utc
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
            w_name, w_date = get_window_and_date(log.timestamp_taken)
            if start_date <= w_date <= end_date:
                taken_set.add((log.med_id, w_name, w_date))

        total_expected = 0
        total_taken = 0
        med_stats = {med.med_id: {"name": med.name, "taken": 0, "expected": 0} for med in meds}

        current_d = start_date
        while current_d <= end_date:
            for med in meds:
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
