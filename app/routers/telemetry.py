from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from datetime import datetime, timezone, timedelta


router = APIRouter(tags=["Telemetry"])

MAX_RECORDS_PER_DEVICE = 1000 # Max telemetry records to keep per device (oldest records will be deleted when limit is exceeded)
security = HTTPBearer()

@router.get("/devices/{device_id}/telemetry", response_model=list[schemas.TelemetryResponse])
def get_device_telemetry(
    device_id: int,
    minutes: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):

    device = db.query(models.Device).filter(models.Device.id == device_id).first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    query = db.query(models.TelemetryRecord).filter(
        models.TelemetryRecord.device_id == device_id
    )

    if minutes is not None:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)

        query = query.filter(
            models.TelemetryRecord.timestamp >= cutoff
        )

    records = (
        query
        .order_by(models.TelemetryRecord.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return records

@router.post("/devices/{device_id}/telemetry", response_model=schemas.TelemetryResponse)
def create_telemetry(
    device_id: int,
    record: schemas.TelemetryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    api_key = credentials.credentials
    # print(f"\033[92mINFO\033[0m:\t {api_key}")
    print(f"{'\033[92m'}INFO{'\033[0m'}:\tTelemetry received | device={device_id} | metric={record.metric_type} | value={record.value}")

    device = db.query(models.Device).filter(models.Device.id == device_id).first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.api_key != api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    device.last_seen = datetime.now(timezone.utc)

    telemetry = models.TelemetryRecord(
        device_id=device_id,
        metric_type=record.metric_type,
        value=record.value
    )

    db.add(telemetry)
    db.commit()
    db.refresh(telemetry)

    count = db.query(models.TelemetryRecord).filter(
        models.TelemetryRecord.device_id == device_id
    ).count()

    if count > MAX_RECORDS_PER_DEVICE:

        oldest_records = (
            db.query(models.TelemetryRecord)
            .filter(models.TelemetryRecord.device_id == device_id)
            .order_by(models.TelemetryRecord.timestamp.asc())
            .limit(count - MAX_RECORDS_PER_DEVICE)
            .all()
        )

        for r in oldest_records:
            db.delete(r)

    db.commit()

    return telemetry