"""
Authentication router: login, me, and change-password
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, log_audit_event
from app.core.config import settings
from app.core.db import get_db
from app.core.errors import ConflictError, UnauthorizedError
from app.core.rate_limit import login_limiter, rate_limit_check
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.entities import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit_check(login_limiter))])
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticates user with email and password via Argon2id.
    Issues JWT access token on success.
    """
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        # Audit failed login attempt
        log_audit_event(
            db,
            action="auth.login_failed",
            resource_type="user",
            resource_id=payload.email,
            ip_address=request.client.host if request.client else None,
        )
        db.commit()
        raise UnauthorizedError(message="Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError(message="User account is deactivated")

    # Issue JWT
    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    # Log successful login
    log_audit_event(
        db,
        action="auth.login_success",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Changes password for the currently authenticated user."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise UnauthorizedError(message="Current password is incorrect")

    if payload.current_password == payload.new_password:
        raise ConflictError(message="New password cannot be the same as current password")

    current_user.password_hash = get_password_hash(payload.new_password)
    log_audit_event(
        db,
        action="auth.password_changed",
        resource_type="user",
        resource_id=str(current_user.id),
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return {"message": "Password updated successfully"}
