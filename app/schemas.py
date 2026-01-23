from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict
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
    model_config = ConfigDict(from_attributes=True)

# Token
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Prescriber
class PrescriberBase(BaseModel):
    name: str
    phone_number: str

class PrescriberCreate(PrescriberBase):
    pass

class PrescriberResponse(PrescriberBase):
    prescriber_id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

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
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbs: Optional[float] = None
    fiber: Optional[float] = None
    sodium: Optional[float] = None
    save_food: Optional[int] = 0

class FoodLogResponse(BaseModel):
    log_id: Optional[int] = None
    food_name: str
    meal_id: str
    calories: float
    serving_size: float
    quantity: float
    timestamp: Optional[datetime] = None

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
    sodium: float = 0.0
    # New Fields (Base, optional for creation to support old API if needed, but good to include)
    brand: Optional[str] = None
    serving_size_unit: Optional[str] = None
    cholesterol: Optional[float] = 0.0
    total_sugars: Optional[float] = 0.0
    added_sugars: Optional[float] = 0.0
    vitamin_d: Optional[float] = 0.0
    calcium: Optional[float] = 0.0
    iron: Optional[float] = 0.0
    potassium: Optional[float] = 0.0
    health_score: Optional[str] = None
    health_insight: Optional[str] = None
    pairing_tip: Optional[str] = None
    serving_weight_grams: Optional[float] = None
    serving_volume_ml: Optional[float] = None

class NutritionCacheCreate(NutritionCacheBase):
    pass

class NutritionCacheUpdate(BaseModel):
    food_name: Optional[str] = None
    barcode: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbs: Optional[float] = None
    fiber: Optional[float] = None
    sodium: Optional[float] = None
    is_user_visible: Optional[bool] = None
    # New Fields
    brand: Optional[str] = None
    serving_size_unit: Optional[str] = None
    cholesterol: Optional[float] = None
    total_sugars: Optional[float] = None
    added_sugars: Optional[float] = None
    vitamin_d: Optional[float] = None
    calcium: Optional[float] = None
    iron: Optional[float] = None
    potassium: Optional[float] = None
    health_score: Optional[str] = None
    health_insight: Optional[str] = None
    pairing_tip: Optional[str] = None
    serving_weight_grams: Optional[float] = None
    serving_volume_ml: Optional[float] = None

class NutritionCacheResponse(NutritionCacheBase):
    food_id: int
    source: str
    is_user_visible: bool
    model_config = ConfigDict(from_attributes=True)

# V2 API Schemas

class V2Metadata(BaseModel):
    name: str
    brand: Optional[str] = None
    upc: Optional[str] = None
    srv_per_cont: Optional[float] = None

class V2Macros(BaseModel):
    calories: float
    fat_g: float
    cholesterol_mg: Optional[float] = 0.0
    sodium_mg: Optional[float] = 0.0
    carbs_g: float
    fiber_g: Optional[float] = 0.0
    total_sugars_g: Optional[float] = 0.0
    added_sugars_g: Optional[float] = 0.0
    protein_g: float

class V2Micros(BaseModel):
    vit_d_mcg: Optional[float] = 0.0
    calcium_mg: Optional[float] = 0.0
    iron_mg: Optional[float] = 0.0
    potassium_mg: Optional[float] = 0.0

class V2ServingInfo(BaseModel):
    size: Optional[str] = None

class V2Analysis(BaseModel):
    score_color: Optional[str] = None
    health_insight: Optional[str] = None
    pairing_tip: Optional[str] = None

class V2FoodItem(BaseModel):
    metadata: V2Metadata
    macros: V2Macros
    micros: Optional[V2Micros] = None
    serving_info: Optional[V2ServingInfo] = None
    analysis: Optional[V2Analysis] = None

class NutritionLogV2(BaseModel):
    quantity: Optional[float] = 1.0
    timestamp: Optional[datetime] = None
    meal: Optional[str] = "Snack"
    variables: Dict[str, V2FoodItem]

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
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

# Recipes

class RecipeIngredientBase(BaseModel):
    food_id: int
    quantity: float
    unit: Optional[str] = None

class RecipeIngredientCreate(RecipeIngredientBase):
    pass

class RecipeIngredientResponse(RecipeIngredientBase):
    ingredient_id: int
    food: NutritionCacheResponse
    model_config = ConfigDict(from_attributes=True)

class RecipeBase(BaseModel):
    name: str
    instructions: Optional[str] = None
    cook_time_minutes: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    total_servings: float = 1.0

class RecipeCreate(RecipeBase):
    ingredients: List[RecipeIngredientCreate]
    health_score: Optional[str] = None
    health_insight: Optional[str] = None
    pairing_tip: Optional[str] = None

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    instructions: Optional[str] = None
    cook_time_minutes: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    total_servings: Optional[float] = None
    ingredients: Optional[List[RecipeIngredientCreate]] = None
    health_score: Optional[str] = None
    health_insight: Optional[str] = None
    pairing_tip: Optional[str] = None

class RecipeResponse(RecipeBase):
    recipe_id: int
    user_id: int
    current_food_id: int
    current_food: NutritionCacheResponse
    ingredients: List[RecipeIngredientResponse]
    model_config = ConfigDict(from_attributes=True)
