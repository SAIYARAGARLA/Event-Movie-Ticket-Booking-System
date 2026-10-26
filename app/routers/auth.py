
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.schemas.schemas import RegisterIn
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.redis_client import get_redis

router = APIRouter(prefix="/auth", tags=["Authentication"])


def rate_limit(key: str, limit: int = 5, window: int = 60):
    try:
        r = get_redis()
        count = r.incr(key)

        if count == 1:
            r.expire(key, window)

        if count > limit:
            raise HTTPException(
                status_code=429,
                detail=f"Too many attempts. Retry in {max(r.ttl(key), 1)} seconds",
            )

    except RuntimeError:
        pass


@router.post("/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email.lower(),
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=data.role,
        is_approved=(data.role == "Customer"),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_approved": user.is_approved,
        "message": (
            "Organizer accounts require admin approval"
            if user.role == "Organizer"
            else "Registered"
        ),
    }


@router.post("/login")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    rate_limit("login:" + ip)

    user = (
        db.query(User)
        .filter(User.email == form_data.username.lower())
        .first()
    )

    if not user or not verify_password(
        form_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Inactive users cannot log in",
        )

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "expires_in_minutes": 30,
        "role": user.role,
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
        "is_approved": user.is_approved,
        "venue_id": user.venue_id,
    }
