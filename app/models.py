from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime, Boolean, Enum, Time
from sqlalchemy.orm import relationship, declarative_base
import datetime
import enum

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    weight_kg = Column(Float)
    height_cm = Column(Float)
    password_hash = Column(String)
    unit_system = Column(String, default="METRIC")
    is_admin = Column(Boolean, default=False)
    timezone = Column(String, default="UTC")
    theme_preference = Column(String, default="SYSTEM") # SYSTEM, LIGHT, DARK

    # New fields
    birth_year = Column(Integer)
    date_of_birth = Column(Date, nullable=True) # Full birthday
    gender = Column(String) # 'M', 'F', 'O'
    goal_weight_kg = Column(Float)
    calorie_goal = Column(Integer)

    # Time Windows (Defaults)
    window_morning_start = Column(Time, default=datetime.time(6, 0))
    window_afternoon_start = Column(Time, default=datetime.time(12, 0))
    window_evening_start = Column(Time, default=datetime.time(17, 0))
    window_bedtime_start = Column(Time, default=datetime.time(21, 0))

    daily_logs = relationship("DailyLog", back_populates="user")
    prescribers = relationship("Prescriber", back_populates="user")
    medications = relationship("Medication", back_populates="user")
    blood_pressures = relationship("BloodPressure", back_populates="user")
    food_item_logs = relationship("FoodItemLog", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    exercise_logs = relationship("ExerciseLog", back_populates="user")
    allergies = relationship("Allergy", back_populates="user")
    vaccinations = relationship("Vaccination", back_populates="user")

class Allergy(Base):
    __tablename__ = "allergies"
    allergy_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    allergen = Column(String)
    reaction = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    user = relationship("User", back_populates="allergies")

class Vaccination(Base):
    __tablename__ = "vaccinations"
    vaccine_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    vaccine_type = Column(String) # Influenza, Covid, Tdap, Shingles Dose 1, Shingles Dose 2
    date_administered = Column(Date)
    user = relationship("User", back_populates="vaccinations")

class SystemConfig(Base):
    __tablename__ = "system_config"
    key = Column(String, primary_key=True)
    value = Column(String)

class DailyLog(Base):
    __tablename__ = "daily_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    date = Column(Date)

    total_calories_consumed = Column(Float, default=0.0)
    total_calories_burned = Column(Float, default=0.0)

    user = relationship("User", back_populates="daily_logs")

class Prescriber(Base):
    __tablename__ = "prescribers"

    prescriber_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    name = Column(String)
    phone_number = Column(String)

    user = relationship("User", back_populates="prescribers")
    medications = relationship("Medication", back_populates="prescriber")

class MedicationType(str, enum.Enum):
    PRESCRIPTION = "PRESCRIPTION"
    OTC = "OTC"

class Medication(Base):
    __tablename__ = "medications"

    med_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    prescriber_id = Column(Integer, ForeignKey("prescribers.prescriber_id"), nullable=True)
    name = Column(String)
    frequency = Column(String)
    type = Column(String) # PRESCRIPTION or OTC
    current_inventory = Column(Integer)
    refills_remaining = Column(Integer)
    daily_doses = Column(Integer, default=1)

    # Schedule Flags
    schedule_morning = Column(Boolean, default=False)
    schedule_afternoon = Column(Boolean, default=False)
    schedule_evening = Column(Boolean, default=False)
    schedule_bedtime = Column(Boolean, default=False)

    # Compliance & Refill
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    refill_quantity = Column(Integer, default=30)

    user = relationship("User", back_populates="medications")
    prescriber = relationship("Prescriber", back_populates="medications")
    dose_logs = relationship("MedDoseLog", back_populates="medication")

class MedDoseLog(Base):
    __tablename__ = "med_dose_logs"

    dose_log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    med_id = Column(Integer, ForeignKey("medications.med_id"))
    timestamp_taken = Column(DateTime, default=datetime.datetime.utcnow)
    target_time_drift = Column(Float)
    dose_window = Column(String, nullable=True)

    medication = relationship("Medication", back_populates="dose_logs")

class BloodPressure(Base):
    __tablename__ = "blood_pressure"

    bp_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    systolic = Column(Integer)
    diastolic = Column(Integer)
    pulse = Column(Integer)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    location = Column(String)
    stress_level = Column(Integer)
    meds_taken_before = Column(String)

    user = relationship("User", back_populates="blood_pressures")

class NutritionSource(str, enum.Enum):
    OFF = "OFF"
    MANUAL = "MANUAL"

class NutritionCache(Base):
    __tablename__ = "nutrition_cache"

    food_id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=True)
    food_name = Column(String)
    calories = Column(Float)
    protein = Column(Float)
    fat = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    fiber = Column(Float, default=0.0)
    source = Column(String) # OFF/MANUAL

    food_item_logs = relationship("FoodItemLog", back_populates="nutrition_info")

class FoodItemLog(Base):
    __tablename__ = "food_item_logs"

    item_log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    meal_id = Column(String)
    food_id = Column(Integer, ForeignKey("nutrition_cache.food_id"))
    serving_size = Column(Float)
    quantity = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="food_item_logs")
    nutrition_info = relationship("NutritionCache", back_populates="food_item_logs")

class ExerciseLog(Base):
    __tablename__ = "exercise_logs"

    exercise_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    activity_type = Column(String)
    duration_minutes = Column(Float)
    calories_burned = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="exercise_logs")

class APIKey(Base):
    __tablename__ = "api_keys"

    key_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    name = Column(String)
    hashed_key = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="api_keys")

class METLookup(Base):
    __tablename__ = "met_lookup"

    met_id = Column(Integer, primary_key=True, index=True)
    activity_name = Column(String, unique=True)
    met_value = Column(Float)
