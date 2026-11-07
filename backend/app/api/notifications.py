from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_notification_service, require_admin
from ..models import Notification
from ..schemas import NotificationOut, NotificationTestRequest
from ..services.notifications import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    user_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    notifications: NotificationService = Depends(get_notification_service),
) -> list[Notification]:
    return notifications.list_for_user(user_id, limit=limit, offset=offset)


@router.post(
    "/test",
    response_model=NotificationOut,
    dependencies=[Depends(require_admin)],
)
def send_test_notification(
    payload: NotificationTestRequest,
    notifications: NotificationService = Depends(get_notification_service),
) -> Notification:
    notification = notifications.notify_test(payload.user_id, payload.title, payload.body)
    if notification is None:
        raise HTTPException(status_code=404, detail="User not found")
    return notification


@router.get("/{notification_id}", response_model=NotificationOut)
def get_notification(notification_id: int, db: Session = Depends(get_db)) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification
