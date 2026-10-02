"""Database layer: Postgres (Neon) in production, SQLite for local dev.

FAIL-FAST RULE: if running in production (RENDER env var set or
ENV=production) and DATABASE_URL is missing, raise immediately.
No silent SQLite fallback in production — that was the data-loss bug.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

log = logging.getLogger("mommy.db")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
IS_PRODUCTION = bool(os.environ.get("RENDER")) or os.environ.get("ENV") == "production"

if IS_PRODUCTION and not DATABASE_URL:
    raise RuntimeError(
        "FATAL: DATABASE_URL is not set in production. Refusing to boot "
        "rather than silently falling back to ephemeral SQLite. "
        "Set DATABASE_URL on the Render service."
    )

USE_POSTGRES = bool(DATABASE_URL)
if not USE_POSTGRES:
    log.warning(
        "!! DATABASE_URL not set — using LOCAL SQLite dev database. "
        "Data will NOT persist on Render. Set DATABASE_URL for production. !!"
    )

_pg_pool = None


def _pg_conn():
    global _pg_pool
    import psycopg

    return psycopg.connect(DATABASE_URL)


@contextmanager
def get_conn():
    """Yield a DB connection. Commits on success, rolls back on error."""
    if USE_POSTGRES:
        conn = _pg_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect("mommy_dev.db")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def q(query: str) -> str:
    """Translate %s placeholders to ? for SQLite."""
    if USE_POSTGRES:
        return query
    return query.replace("%s", "?")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


SCHEMA_PG = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    display_name TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free','pro','team','admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    idea_text TEXT NOT NULL,
    description TEXT,
    lifecycle_stage TEXT NOT NULL DEFAULT 'idea'
        CHECK (lifecycle_stage IN ('idea','plan','build','test','evidence','verify','protect','release','publish','own')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (owner_id, slug)
);
CREATE TABLE IF NOT EXISTS requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    req_code TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'functional',
    verification_kind TEXT NOT NULL DEFAULT 'ai' CHECK (verification_kind IN ('ai','human','both')),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','approved','in_progress','implemented','verified','blocked','failed')),
    origin TEXT NOT NULL DEFAULT 'ai' CHECK (origin IN ('ai','human','imported')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, req_code)
);
"""

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    display_name TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free','pro','team','admin')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    idea_text TEXT NOT NULL,
    description TEXT,
    lifecycle_stage TEXT NOT NULL DEFAULT 'idea'
        CHECK (lifecycle_stage IN ('idea','plan','build','test','evidence','verify','protect','release','publish','own')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (owner_id, slug)
);
CREATE TABLE IF NOT EXISTS requirements (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    req_code TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'functional',
    verification_kind TEXT NOT NULL DEFAULT 'ai' CHECK (verification_kind IN ('ai','human','both')),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','approved','in_progress','implemented','verified','blocked','failed')),
    origin TEXT NOT NULL DEFAULT 'ai' CHECK (origin IN ('ai','human','imported')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (project_id, req_code)
);
"""


def init_schema() -> None:
    schema = SCHEMA_PG if USE_POSTGRES else SCHEMA_SQLITE
    with get_conn() as conn:
        cur = conn.cursor()
        # sqlite3 can't run multiple statements via execute(); split them
        if USE_POSTGRES:
            cur.execute(schema)
        else:
            for stmt in schema.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
    log.info("schema ready (postgres=%s)", USE_POSTGRES)
