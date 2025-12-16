from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import database, models, schemas, auth

router = APIRouter(
    prefix="/api/v1/prescribers",
    tags=["prescribers"]
)

@router.post("/", response_model=schemas.PrescriberResponse)
def create_prescriber(
    prescriber: schemas.PrescriberCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_prescriber = models.Prescriber(**prescriber.dict(), user_id=current_user.user_id)
    db.add(db_prescriber)
    db.commit()
    db.refresh(db_prescriber)
    return db_prescriber

@router.get("/", response_model=List[schemas.PrescriberResponse])
def read_prescribers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    prescribers = db.query(models.Prescriber).filter(models.Prescriber.user_id == current_user.user_id).offset(skip).limit(limit).all()
    return prescribers
