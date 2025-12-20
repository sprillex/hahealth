from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import database, models, schemas, auth, services

router = APIRouter(
    prefix="/api/webhook",
    tags=["webhook"]
)

@router.post("/health")
def webhook_ingestion(
    payload: schemas.WebhookPayload,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(auth.verify_webhook_api_key)
):
    service_health = services.HealthLogService()
    service_med = services.MedicationService()

    if payload.data_type == schemas.WebhookDataType.BLOOD_PRESSURE:
        data = schemas.BPPayload(**payload.payload)
        service_health.log_bp(db, user.user_id, data)
        return {"status": "success", "message": "Blood pressure logged"}

    elif payload.data_type == schemas.WebhookDataType.MEDICATION_TAKEN:
        data = schemas.MedicationTakenPayload(**payload.payload)
        log, alert = service_med.log_dose(db, user.user_id, data.med_name, data.timestamp, data.dose_window)
        if not log:
            # Return 400 Bad Request instead of 404 so user knows endpoint exists but data is invalid
            raise HTTPException(status_code=400, detail=alert)
        return {"status": "success", "message": "Medication logged", "alert": alert}

    elif payload.data_type == schemas.WebhookDataType.EXERCISE_SESSION:
        data = schemas.ExercisePayload(**payload.payload)
        service_health.log_exercise(db, user, data)
        return {"status": "success", "message": "Exercise logged"}

    elif payload.data_type == schemas.WebhookDataType.FOOD_LOG:
        data = schemas.FoodLogPayload(**payload.payload)
        item, error = service_health.log_food(db, user, data)
        if error:
             raise HTTPException(status_code=400, detail=error)
        return {"status": "success", "message": "Food logged"}

    else:
        raise HTTPException(status_code=400, detail="Invalid Data Type")
