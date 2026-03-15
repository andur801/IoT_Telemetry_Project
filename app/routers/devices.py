from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import models, schemas
from app.database import get_db
from datetime import datetime, timezone
import secrets

router = APIRouter(prefix="/devices", tags=["Devices"])

DEVICE_ONLINE_THRESHOLD = 60  # How long before device will be offline in seconds

@router.post("", response_model=schemas.DeviceResponse)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):

    owner = db.query(models.User).filter(models.User.id == device.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner user not found")

    device_data = device.model_dump()

    device_data["api_key"] = secrets.token_hex(16)

    db_device = models.Device(**device_data)

    db.add(db_device)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid device data")

    db.refresh(db_device)

    device_dict = db_device.__dict__.copy()
    device_dict["status"] = "offline"

    return device_dict

@router.get("", response_model=list[schemas.DeviceResponse])
def list_devices(db: Session = Depends(get_db)):

    devices = db.query(models.Device).all()
    now = datetime.now(timezone.utc)

    for device in devices:
        last_seen = device.last_seen.replace(tzinfo=timezone.utc)
        delta = (now - last_seen).total_seconds()
        device.status = "online" if delta < DEVICE_ONLINE_THRESHOLD else "offline"

    return devices