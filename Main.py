from fastapi import (
    FastAPI,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AppSetting, Subscription, SongRequest
from app.auth import get_current_user
from app.admin import router as admin_router
from app.services.quota import (
    reserve_song,
    has_premium
)


app = FastAPI(
    title="ABHISHEK MUSIC API",
    version="2.0.0",
    description="ABHISHEK MUSIC backend"
)


app.include_router(admin_router)


@app.get("/")
def home():
    return {
        "project": "ABHISHEK MUSIC",
        "backend": "online",
        "version": "2.0.0"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/app/status")
def app_status(db: Session = Depends(get_db)):
    s = db.get(AppSetting, 1)

    if s is None:
        return {
            "app_enabled": True,
            "maintenance_mode": False,
            "force_update": False,
            "minimum_version": "1.0.0"
        }

    return {
        "app_enabled": s.app_enabled,
        "maintenance_mode": s.maintenance_mode,
        "force_update": s.force_update,
        "minimum_version": s.minimum_version,
        "update_message": s.update_message
    }


def check_app_status(db):
    s = db.get(AppSetting, 1)

    if s and not s.app_enabled:
        raise HTTPException(
            status_code=503,
            detail="ABHISHEK MUSIC is currently disabled"
        )

    if s and s.maintenance_mode:
        raise HTTPException(
            status_code=503,
            detail="App is under maintenance"
        )


@app.get("/me")
def my_profile(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    check_app_status(db)

    return {
        "uid": user.id,
        "email": user.email,
        "display_name": user.display_name
    }


@app.get("/subscription/status")
def subscription_status(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    check_app_status(db)

    return {
        "premium": has_premium(db, user.id),
        "plans": [
            "monthly",
            "yearly",
            "lifetime"
        ]
    }


@app.get("/songs/quota")
def song_quota(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    check_app_status(db)

    used = db.query(SongRequest).filter(
        SongRequest.user_id == user.id
    ).count()

    premium = has_premium(db, user.id)

    return {
        "premium": premium,
        "free_limit": 2,
        "used": used,
        "remaining": None if premium else max(0, 2 - used)
    }


@app.post("/songs/reserve")
def create_song_reservation(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    check_app_status(db)

    return reserve_song(db, user)
