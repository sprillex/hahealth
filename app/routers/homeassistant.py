from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import database, models, auth, services

router = APIRouter(
    prefix="/api/v1/homeassistant",
    tags=["homeassistant"]
)

@router.get("/sensors")
def get_homeassistant_sensors(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(auth.verify_webhook_api_key)
):
    health_service = services.HealthLogService()
    sensor_data = health_service.get_sensor_data(db, user)
    return sensor_data
