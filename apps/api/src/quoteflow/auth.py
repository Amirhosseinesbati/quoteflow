"""Server-side sessions and workspace-scoped role checks."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import SessionRecord, User, Workspace

COOKIE_NAME = "quoteflow_session"
ROLE_RANK = {"viewer": 0, "operator": 1, "admin": 2}


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(db: Session, user: User, response: Response) -> None:
    settings = get_settings()
    raw = secrets.token_urlsafe(48)
    db.add(
        SessionRecord(
            user_id=user.id,
            token_hash=token_digest(raw),
            expires_at=datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours),
        )
    )
    db.commit()
    response.set_cookie(
        COOKIE_NAME,
        raw,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.session_secure,
        samesite="lax",
        path="/",
    )


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        raise HTTPException(401, "Authentication required")
    record = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == token_digest(raw)))
    if record is None or _utc(record.expires_at) <= datetime.now(UTC):
        raise HTTPException(401, "Session expired")
    user = db.get(User, record.user_id)
    if user is None or not user.active:
        raise HTTPException(401, "User unavailable")
    if get_settings().mode.upper() != "DEMO":
        workspace = db.get(Workspace, user.workspace_id)
        if workspace is None or workspace.is_demo:
            raise HTTPException(401, "Demo session is unavailable in connected mode")
    return user


def require_role(minimum: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if ROLE_RANK.get(user.role, -1) < ROLE_RANK[minimum]:
            raise HTTPException(403, "Permission denied")
        return user

    return dependency


def login(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email, User.active.is_(True)))
    if user and get_settings().mode.upper() != "DEMO":
        workspace = db.get(Workspace, user.workspace_id)
        if workspace is None or workspace.is_demo:
            return None
    if user and PasswordHash.recommended().verify(password, user.password_hash):
        return user
    return None


def demo_user(db: Session, workspace_slug: str, role: str) -> User:
    if get_settings().mode.upper() != "DEMO":
        raise HTTPException(404, "Demo access is disabled")
    if workspace_slug not in ("arc-field-demo", "arc-field-isolation") or role not in ROLE_RANK:
        raise HTTPException(422, "Unknown demo workspace or role")
    workspace = db.scalar(
        select(Workspace).where(Workspace.slug == workspace_slug, Workspace.is_demo.is_(True))
    )
    if workspace is None:
        raise HTTPException(503, "Demo data not initialized")
    user = db.scalar(select(User).where(User.workspace_id == workspace.id, User.role == role))
    if user is None:
        raise HTTPException(503, "Demo user not initialized")
    return user
