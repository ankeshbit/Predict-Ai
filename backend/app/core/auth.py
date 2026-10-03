"""
Authentication dependencies and Role-Based Access Control (RBAC) enforcement
"""

import uuid
from typing import Any, Callable, Dict, List, Optional

from app.core.db import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models.entities import AuditLog, User
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extracts Bearer token from Authorization header and returns the authenticated User.
    """
    if not auth_header or not auth_header.credentials:
        raise UnauthorizedError(message="Authentication token is missing")

    token = auth_header.credentials
    payload = decode_access_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError(message="Invalid token payload")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError(message="Malformed user identifier in token")

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise UnauthorizedError(message="User not found")
    if not user.is_active:
        raise ForbiddenError(message="User account is deactivated")

    return user


def require_roles(allowed_roles: List[str]) -> Callable[[User], User]:
    """
    Dependency factory that restricts route access to specified roles.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(
                message=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker


# Predefined RBAC dependencies
get_current_engineer = require_roles(["engineer", "admin"])
get_current_admin = require_roles(["admin"])


def log_audit_event(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Records an immutable audit log entry in the audit_log table.
    """
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(audit)
    db.flush()
    return audit
