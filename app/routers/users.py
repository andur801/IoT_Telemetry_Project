from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import models, schemas
from app.database import get_db
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("", response_model=schemas.UserResponse)
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


@router.get("", response_model=list[schemas.UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()