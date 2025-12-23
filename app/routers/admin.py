from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app import database, models, auth, services, mqtt
import os

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"]
)

def get_current_admin(current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

@router.get("/mqtt_status")
def get_mqtt_status(admin: models.User = Depends(get_current_admin)):
    return mqtt.mqtt_client.get_status()

@router.post("/key")
def set_backup_key(
    key_data: dict,
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(get_current_admin)
):
    key = key_data.get("key")
    if not key or len(key) < 8:
        raise HTTPException(status_code=400, detail="Key must be at least 8 chars")

    service = services.BackupService()
    service.set_key(db, key)
    return {"message": "Backup key updated"}

@router.post("/backup")
def create_backup(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(get_current_admin)
):
    service = services.BackupService()
    try:
        filename = service.create_backup(db)
        return {"message": "Backup created", "filename": filename}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/backup/latest")
def download_latest_backup(
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(get_current_admin)
):
    service = services.BackupService()
    path = service.get_latest_backup()
    if not path:
        raise HTTPException(status_code=404, detail="No backups found")

    return FileResponse(path, filename=os.path.basename(path), media_type='application/octet-stream')

@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    admin: models.User = Depends(get_current_admin)
):
    service = services.BackupService()
    content = await file.read()
    try:
        service.restore_backup(db, content)
        return {"message": "Database restored successfully. Server logic may require restart."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
