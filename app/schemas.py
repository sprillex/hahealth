from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from enum import Enum

# User
class UserBase(BaseModel):
    name: str
    weight_kg: float
    height_cm: float
    birth_year: Optional[int] = None
    gender: Optional[str] = None
    goal_weight_kg: Optional[float] = None
    calorie_goal: Optional[int] = None

class UserCreate(UserBase):
    password: str
    unit_system: str = "METRIC"

class UserUpdate(BaseModel):
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    unit_system: Optional[str] = None
    birth_year: Optional[int] = None
    gender: Optional[str] = None
    goal_weight_kg: Optional[float] = None
    calorie_goal: Optional[int] = None

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class UserResponse(UserBase):
    user_id: int
    unit_system: str
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

class ExercisePayload(BaseModel):
    duration_minutes: float
    calories_burned: Optional[float] = None
    activity_type: str # Needed for MET lookup if cals missing? Plan says "MET Formula" using duration.
    # We might need a MET table or lookup.

class FoodLogPayload(BaseModel):
    barcode: Optional[str] = None
    food_name: Optional[str] = None
    serving_size: float = 1.0
    quantity: float = 1.0
    meal_id: str = "Snack"

# Nutrition
class NutritionCacheResponse(BaseModel):
    food_id: int
    barcode: Optional[str]
    food_name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    source: str
    class Config:
        from_attributes = True
