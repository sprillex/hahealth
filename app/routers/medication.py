from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from app import database, models, schemas, auth, services

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
    db_med = models.Medication(**med.model_dump(), user_id=current_user.user_id)
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

@router.put("/{med_id}", response_model=schemas.MedicationResponse)
def update_medication(
    med_id: int,
    med: schemas.MedicationCreate, # Reusing Create schema as Update usually has same fields
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_med = db.query(models.Medication).filter(models.Medication.med_id == med_id, models.Medication.user_id == current_user.user_id).first()
    if not db_med:
        raise HTTPException(status_code=404, detail="Medication not found")

    # Update fields
    # Iterate over schema fields and update
    data = med.dict(exclude_unset=True)
    for key, value in data.items():
        setattr(db_med, key, value)

    db.commit()
    db.refresh(db_med)
    return db_med

@router.get("/log")
def read_medication_logs(
    date_str: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = date.today()

    import zoneinfo
    from datetime import timezone
    try:
        user_tz = zoneinfo.ZoneInfo(current_user.timezone) if current_user.timezone else timezone.utc
    except Exception:
        user_tz = timezone.utc

    # Local day start/end
    # Using naive combine and then attaching timezone
    local_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=user_tz)
    local_end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=user_tz)

    # Convert to UTC for DB Query
    utc_start = local_start.astimezone(timezone.utc)
    utc_end = local_end.astimezone(timezone.utc)

    # Query logs + join Med to get name
    logs = db.query(
        models.MedDoseLog.dose_log_id,
        models.MedDoseLog.med_id,
        models.MedDoseLog.timestamp_taken,
        models.Medication.name,
        models.MedDoseLog.dose_window
    ).join(
        models.Medication, models.MedDoseLog.med_id == models.Medication.med_id
    ).filter(
        models.MedDoseLog.user_id == current_user.user_id,
        models.MedDoseLog.timestamp_taken >= utc_start,
        models.MedDoseLog.timestamp_taken <= utc_end
    ).order_by(models.MedDoseLog.timestamp_taken.desc()).all()

    from datetime import timezone
    results = []
    for log in logs:
        name = log.name
        if log.dose_window:
             name += f" - {log.dose_window[0].upper()}"

        ts = log.timestamp_taken
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        results.append({
            "log_id": log.dose_log_id,
            "med_id": log.med_id,
            "med_name": name,
            "timestamp": ts,
            "dose_window": log.dose_window
        })
    return results

@router.delete("/log/{log_id}")
def delete_med_log(
    log_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.MedicationService()
    success = service.delete_dose_log(db, log_id, current_user.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Log not found")
    return {"status": "success"}

@router.put("/log/{log_id}", response_model=schemas.MedicationLogResponse)
def update_med_log(
    log_id: int,
    updates: schemas.LogUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.MedicationService()
    log = service.update_dose_log(db, log_id, current_user.user_id, updates)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    # We need to return proper response structure.
    # Log object has med_id, need name.
    med = db.query(models.Medication).filter(models.Medication.med_id == log.med_id).first()

    ts = log.timestamp_taken
    if ts and ts.tzinfo is None:
        from datetime import timezone
        ts = ts.replace(tzinfo=timezone.utc)

    return {
        "log_id": log.dose_log_id,
        "med_id": log.med_id,
        "med_name": med.name if med else "Unknown",
        "timestamp": ts,
        "dose_window": log.dose_window
    }

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

    # Logic: update stock with refill.quantity (or med.refill_quantity if available?)
    # The payload 'refill.quantity' is passed from frontend.
    # The user said: "when it it pressed it should update both the stock and it should decremnt the number of refills left."
    # We should assume the payload quantity IS the quantity to add.

    med.current_inventory += refill.quantity

    if med.refills_remaining > 0:
        med.refills_remaining -= 1

    db.commit()
    db.refresh(med)
    return med
