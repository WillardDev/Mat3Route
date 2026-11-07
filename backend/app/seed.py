from __future__ import annotations

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import AppUser, NotificationDevice, Route


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        route = db.scalar(select(Route).order_by(Route.id).limit(1))
        if route is None:
            print("No routes found. Run scripts/setup_routes_db.sh first.")
            return

        demo_users = [
            ("+254700000001", "Demo Commuter One", "demo-subscriber-1"),
            ("+254700000002", "Demo Commuter Two", "demo-subscriber-2"),
        ]
        for phone, name, token in demo_users:
            user = db.scalar(select(AppUser).where(AppUser.phone == phone))
            if user is None:
                user = AppUser(
                    phone=phone,
                    name=name,
                    city="Nairobi",
                    route_id=route.id,
                )
                db.add(user)
                db.flush()
                print(f"created user {user.id}: {phone}")
            else:
                user.route_id = route.id
                print(f"updated user {user.id}: {phone}")

            device = db.scalar(
                select(NotificationDevice).where(
                    NotificationDevice.provider == "thrivewave",
                    NotificationDevice.token == token,
                )
            )
            if device is None:
                db.add(
                    NotificationDevice(
                        user_id=user.id,
                        provider="thrivewave",
                        token=token,
                        platform="web",
                    )
                )
                print(f"  registered device token {token}")

        db.commit()
        print(f"demo users subscribed to route {route.route_number} ({route.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
