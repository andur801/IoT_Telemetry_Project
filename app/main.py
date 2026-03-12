from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from contextlib import asynccontextmanager
from .database import engine, Base, get_db
from . import models, schemas
from .security import hash_password
from datetime import datetime, timezone, timedelta
import secrets

MAX_RECORDS_PER_DEVICE = 1000 # Max telemetry records to keep per device (oldest records will be deleted when limit is exceeded)
DEVICE_ONLINE_THRESHOLD = 60  # How long before device will be offline in seconds
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        print(f"{'\033[92m'}INFO{'\033[0m'}:\tDatabase connected successfully.")
    except OperationalError:
        print(f"{'\033[91m'}FAIL{'\033[0m'}:\tDatabase connection failed. Is Docker running?")

    yield


app = FastAPI(lifespan=lifespan)

# --- User Endpoints ---

@app.post("/users", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    hashed_pw = hash_password(user.password)

    db_user = models.User(
        email=user.email,
        hashed_password=hashed_pw
    )

    db.add(db_user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")

    db.refresh(db_user)
    return db_user


@app.get("/users", response_model=list[schemas.UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

# --- Device Endpoints ---

@app.post("/devices", response_model=schemas.DeviceResponse)
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

@app.get("/devices", response_model=list[schemas.DeviceResponse])
def list_devices(db: Session = Depends(get_db)):

    devices = db.query(models.Device).all()
    now = datetime.now(timezone.utc)

    for device in devices:
        last_seen = device.last_seen.replace(tzinfo=timezone.utc)
        delta = (now - last_seen).total_seconds()

        device.status = "online" if delta < DEVICE_ONLINE_THRESHOLD else "offline"

    return devices
,,
# --- Telemetry Endpoints ---

@app.post("/devices/{device_id}/telemetry", response_model=schemas.TelemetryResponse)
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

# @app.post("/telemetry", response_model=schemas.TelemetryResponse)
# def create_telemetry(record: schemas.TelemetryCreate, db: Session = Depends(get_db)):
#
#     print(f"{'\033[92m'}INFO{'\033[0m'}:\tTelemetry received | device={record.device_id} | metric={record.metric_type} | value={record.value}")
#     device = db.query(models.Device).filter(
#         models.Device.id == record.device_id
#     ).first()
#
#     if not device:
#         raise HTTPException(status_code=404, detail="Device not found")
#
#     if device.api_key != record.api_key:
#         raise HTTPException(status_code=403, detail="Invalid device API key")
#
#     telemetry = models.TelemetryRecord(
#         device_id=record.device_id,
#         metric_type=record.metric_type,
#         value=record.value
#     )
#
#     db.add(telemetry)
#     db.commit()
#     db.refresh(telemetry)
#
#     count = db.query(models.TelemetryRecord).filter(
#         models.TelemetryRecord.device_id == record.device_id
#     ).count()
#
#     if count > MAX_RECORDS_PER_DEVICE:
#
#         oldest_records = (
#             db.query(models.TelemetryRecord)
#             .filter(models.TelemetryRecord.device_id == record.device_id)
#             .order_by(models.TelemetryRecord.timestamp.asc())
#             .limit(count - MAX_RECORDS_PER_DEVICE)
#             .all()
#         )
#
#         for r in oldest_records:
#             db.delete(r)
#
#     db.commit()
#
#     return telemetry


@app.get("/devices/{device_id}/telemetry", response_model=list[schemas.TelemetryResponse])
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