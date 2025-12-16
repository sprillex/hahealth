from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import database, models, schemas, auth

router = APIRouter(
    prefix="/api/v1/medications",
    tags=["medications"]
)

@router.post("/", response_model=schemas.MedicationResponse)
def create_medication(
    med: schemas.MedicationCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_med = models.Medication(**med.dict(), user_id=current_user.user_id)
    db.add(db_med)
    db.commit()
    db.refresh(db_med)
    return db_med

@router.get("/", response_model=List[schemas.MedicationResponse])
def read_medications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    meds = db.query(models.Medication).filter(models.Medication.user_id == current_user.user_id).offset(skip).limit(limit).all()
    return meds

@router.post("/{med_id}/refill", response_model=schemas.MedicationResponse)
def refill_medication(
    med_id: int,
    refill: schemas.MedicationRefill,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    med = db.query(models.Medication).filter(models.Medication.med_id == med_id, models.Medication.user_id == current_user.user_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")

    med.current_inventory += refill.quantity
    # Logic for refilling "refills_remaining" is vague in plan ("Log supply addition").
    # Usually you use a refill to add inventory, reducing refills_remaining.
    if med.refills_remaining > 0:
        med.refills_remaining -= 1

    db.commit()
    db.refresh(med)
    return med
