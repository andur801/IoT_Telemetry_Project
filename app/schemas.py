from pydantic import BaseModel, EmailStr
from datetime import datetime

# --- Schemas for User ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True  # For SQLAlchemy compatibility

class UserPublic(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True

# --- Schemas for Device ---

class DeviceCreate(BaseModel):
    name: str
    ip_address: str
    device_type: str
    owner_id: int


class DeviceResponse(BaseModel):
    id: int
    name: str
    ip_address: str
    device_type: str | None
    owner_id: int
    api_key: str
    last_seen: datetime
    status: str

    class Config:
        from_attributes = True

# --- Schemas for TelemetryRecord ---

class TelemetryCreate(BaseModel):
    metric_type: str
    value: float


class TelemetryResponse(BaseModel):
    id: int
    device_id: int
    metric_type: str
    value: float
    timestamp: datetime

    class Config:
        from_attributes = True