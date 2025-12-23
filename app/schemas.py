from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, time
from enum import Enum

# User
class UserBase(BaseModel):
    name: str
    weight_kg: float
    height_cm: float
    birth_year: Optional[int] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    goal_weight_kg: Optional[float] = None
    calorie_goal: Optional[int] = None
    timezone: str = "UTC"
    theme_preference: str = "SYSTEM"

class UserCreate(UserBase):
    password: str
    unit_system: str = "METRIC"

class UserUpdate(BaseModel):
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    unit_system: Optional[str] = None
    birth_year: Optional[int] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    goal_weight_kg: Optional[float] = None
    calorie_goal: Optional[int] = None
    timezone: Optional[str] = None
    theme_preference: Optional[str] = None

    # Time Windows
    window_morning_start: Optional[time] = None
    window_afternoon_start: Optional[time] = None
    window_evening_start: Optional[time] = None
    window_bedtime_start: Optional[time] = None

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class UserResponse(UserBase):
    user_id: int
    unit_system: str
    is_admin: bool
    theme_preference: str
    window_morning_start: Optional[time] = None
    window_afternoon_start: Optional[time] = None
    window_evening_start: Optional[time] = None
    window_bedtime_start: Optional[time] = None
    class Config:
        from_attributes = True

# Token
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Prescriber
class PrescriberBase(BaseModel):
    name: str
    phone_number: str

class PrescriberCreate(PrescriberBase):
    pass

class PrescriberResponse(PrescriberBase):
    prescriber_id: int
    user_id: int
    class Config:
        from_attributes = True

# Medication
class MedicationBase(BaseModel):
    name: str
    frequency: str
    type: str
    current_inventory: int
    refills_remaining: int
    daily_doses: int = 1
    prescriber_id: Optional[int] = None

    # Schedule Flags
    schedule_morning: bool = False
    schedule_afternoon: bool = False
    schedule_evening: bool = False
    schedule_bedtime: bool = False

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    refill_quantity: Optional[int] = 30

class MedicationCreate(MedicationBase):
    pass

class MedicationResponse(MedicationBase):
    med_id: int
    user_id: int
    class Config:
        from_attributes = True

class MedicationRefill(BaseModel):
    quantity: int

# Blood Pressure
class BloodPressureBase(BaseModel):
    systolic: int
    diastolic: int
    pulse: int
    location: str
    stress_level: int
    meds_taken_before: str

class BloodPressureCreate(BloodPressureBase):
    pass

class BloodPressureResponse(BloodPressureBase):
    bp_id: int
    user_id: int
    timestamp: datetime
    class Config:
        from_attributes = True

# Webhook Types
class WebhookDataType(str, Enum):
    BLOOD_PRESSURE = "BLOOD_PRESSURE"
    MEDICATION_TAKEN = "MEDICATION_TAKEN"
    EXERCISE_SESSION = "EXERCISE_SESSION"
    FOOD_LOG = "FOOD_LOG"
    WEIGHT = "WEIGHT"

class WebhookPayload(BaseModel):
    data_type: WebhookDataType
    payload: dict

# Specific Payloads for Webhook
class BPPayload(BaseModel):
    systolic: int
    diastolic: int
    pulse: int
    location: str
    stress_level: int
    meds_taken_before: str

class MedicationTakenPayload(BaseModel):
    med_name: str # Using name to lookup
    timestamp: Optional[datetime] = None
    med_window: Optional[str] = None

class MedicationLogResponse(BaseModel):
    log_id: int
    med_name: str
    timestamp: datetime
    dose_window: Optional[str] = None
    med_id: int

class ExercisePayload(BaseModel):
    duration_minutes: float
    calories_burned: Optional[float] = None
    activity_type: str

class ExerciseLogResponse(BaseModel):
    log_id: int
    activity_type: str
    duration_minutes: float
    calories_burned: float
    timestamp: datetime

class FoodLogPayload(BaseModel):
    barcode: Optional[str] = None
    food_name: Optional[str] = None
    serving_size: float = 1.0
    quantity: float = 1.0
    meal_id: str = "Snack"

class FoodLogResponse(BaseModel):
    log_id: int
    food_name: str
    meal_id: str
    calories: float
    serving_size: float
    quantity: float
    timestamp: datetime

class WeightPayload(BaseModel):
    weight: float
    unit: str = "kg"

class LogUpdate(BaseModel):
    # Generic update fields, specific logic in service
    timestamp: Optional[datetime] = None
    # For Meds
    med_id: Optional[int] = None # If changing the med
    dose_window: Optional[str] = None
    # For Exercise
    duration_minutes: Optional[float] = None
    calories_burned: Optional[float] = None
    activity_type: Optional[str] = None
    # For Food
    quantity: Optional[float] = None
    serving_size: Optional[float] = None
    meal_id: Optional[str] = None

# Nutrition
class NutritionCacheBase(BaseModel):
    barcode: Optional[str] = None
    food_name: str
    calories: float
    protein: float = 0.0
    fat: float = 0.0
    carbs: float = 0.0
    fiber: float = 0.0

class NutritionCacheCreate(NutritionCacheBase):
    pass

class NutritionCacheResponse(NutritionCacheBase):
    food_id: int
    source: str
    class Config:
        from_attributes = True

# Medical History
class AllergyBase(BaseModel):
    allergen: str
    reaction: Optional[str] = None
    severity: Optional[str] = None

class AllergyCreate(AllergyBase):
    pass

class AllergyResponse(AllergyBase):
    allergy_id: int
    user_id: int
    class Config:
        from_attributes = True

class VaccinationBase(BaseModel):
    vaccine_type: str
    date_administered: date

class VaccinationCreate(VaccinationBase):
    pass

class VaccinationResponse(VaccinationBase):
    vaccine_id: int
    user_id: int
    status: Optional[str] = None # For report (Overdue, etc)
    next_due: Optional[date] = None
    class Config:
        from_attributes = True
