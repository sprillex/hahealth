from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import database, models, schemas, auth

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"]
)

@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.name == user.name).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        name=user.name,
        weight_kg=user.weight_kg,
        height_cm=user.height_cm,
        password_hash=hashed_password,
        unit_system=user.unit_system
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@router.put("/me", response_model=schemas.UserResponse)
def update_user_profile(
    user_update: schemas.UserUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if user_update.weight_kg is not None:
        current_user.weight_kg = user_update.weight_kg
    if user_update.height_cm is not None:
        current_user.height_cm = user_update.height_cm
    if user_update.unit_system is not None:
        current_user.unit_system = user_update.unit_system.upper()

    # Profile Fields
    if user_update.birth_year is not None:
        current_user.birth_year = user_update.birth_year
    if user_update.gender is not None:
        current_user.gender = user_update.gender
    if user_update.goal_weight_kg is not None:
        current_user.goal_weight_kg = user_update.goal_weight_kg
    if user_update.calorie_goal is not None:
        current_user.calorie_goal = user_update.calorie_goal
    if user_update.timezone is not None:
        current_user.timezone = user_update.timezone

    # Time Windows
    if user_update.window_morning_start is not None:
        current_user.window_morning_start = user_update.window_morning_start
    if user_update.window_afternoon_start is not None:
        current_user.window_afternoon_start = user_update.window_afternoon_start
    if user_update.window_evening_start is not None:
        current_user.window_evening_start = user_update.window_evening_start
    if user_update.window_bedtime_start is not None:
        current_user.window_bedtime_start = user_update.window_bedtime_start

    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/me/password")
def change_password(
    password_update: schemas.PasswordUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if password_update.new_password != password_update.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")

    if not auth.verify_password(password_update.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    current_user.password_hash = auth.get_password_hash(password_update.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
