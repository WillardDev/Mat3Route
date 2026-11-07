from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AppUser, NotificationDevice, Route
from ..schemas import DeviceCreate, DeviceOut, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> AppUser:
    if db.scalar(select(AppUser.id).where(AppUser.phone == payload.phone)):
        raise HTTPException(status_code=409, detail="A user with this phone already exists")
    if payload.route_id is not None and db.get(Route, payload.route_id) is None:
        raise HTTPException(status_code=404, detail="Route not found")

    user = AppUser(**payload.model_dump())
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="User could not be created") from exc
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> AppUser:
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> AppUser:
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.route_id is not None and db.get(Route, payload.route_id) is None:
        raise HTTPException(status_code=404, detail="Route not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/{user_id}/devices",
    response_model=DeviceOut,
    status_code=status.HTTP_201_CREATED,
)
def register_device(
    user_id: int, payload: DeviceCreate, db: Session = Depends(get_db)
) -> NotificationDevice:
    if db.get(AppUser, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    device = NotificationDevice(user_id=user_id, **payload.model_dump())
    db.add(device)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This device token is already registered"
        ) from exc
    db.refresh(device)
    return device


@router.get("/{user_id}/devices", response_model=list[DeviceOut])
def list_devices(user_id: int, db: Session = Depends(get_db)) -> list[NotificationDevice]:
    if db.get(AppUser, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    return list(
        db.scalars(
            select(NotificationDevice)
            .where(NotificationDevice.user_id == user_id)
            .order_by(NotificationDevice.id)
        )
    )


@router.delete("/{user_id}/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(user_id: int, device_id: int, db: Session = Depends(get_db)) -> None:
    device = db.get(NotificationDevice, device_id)
    if device is None or device.user_id != user_id:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()
