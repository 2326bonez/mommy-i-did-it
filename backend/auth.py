"""Auth: bcrypt passwords + JWT bearer sessions. No secrets in logs."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import get_conn, new_id, now_iso, q

log = logging.getLogger("mommy.auth")

JWT_SECRET = os.environ.get("JWT_SECRET", "")
if not JWT_SECRET:
    # Dev-only fallback; production MUST set JWT_SECRET.
    log.warning("!! JWT_SECRET not set — using insecure dev fallback. Set JWT_SECRET in production. !!")
    JWT_SECRET = "dev-only-insecure-secret-change-me"

JWT_ALGO = "HS256"
JWT_TTL_HOURS = 24

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def make_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_TTL_HOURS)
    return jwt.encode({"sub": user_id, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGO)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session token.")
    user_id = payload.get("sub")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            q("SELECT id, email, display_name, tier FROM users WHERE id = %s"),
            (user_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="User not found.")
    return {"id": row[0], "email": row[1], "display_name": row[2], "tier": row[3]}


def create_user(email: str, password: str, display_name: str) -> dict:
    email = email.strip().lower()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q("SELECT id FROM users WHERE email = %s"), (email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="An account with that email already exists.")
        uid, now = new_id(), now_iso()
        cur.execute(
            q(
                "INSERT INTO users (id, email, password_hash, display_name, tier, created_at, updated_at)"
                " VALUES (%s, %s, %s, %s, 'free', %s, %s)"
            ),
            (uid, email, hash_password(password), display_name.strip() or email.split("@")[0], now, now),
        )
    log.info("user created: %s", email)
    return {"id": uid, "email": email, "display_name": display_name.strip() or email.split("@")[0]}


def authenticate(email: str, password: str) -> dict:
    email = email.strip().lower()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            q("SELECT id, email, password_hash, display_name, tier FROM users WHERE email = %s"),
            (email,),
        )
        row = cur.fetchone()
    if row is None or not row[2] or not verify_password(password, row[2]):
        # Same message either way: don't leak which emails exist.
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"id": row[0], "email": row[1], "display_name": row[3], "tier": row[4]}
