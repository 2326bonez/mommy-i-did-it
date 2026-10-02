"""Mommy I Did It — Phase 0 API.

Auth + Projects + AI requirement generation.
Serves the built React frontend from ../frontend/dist.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import auth as auth_mod
import db as db_mod
from requirements_ai import _slugify, generate_requirements

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("mommy")

# db import runs the DATABASE_URL fail-fast check.
db_mod.init_schema()

app = FastAPI(title="Mommy I Did It", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- schemas ----------

class SignupIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=80)


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    idea_text: str = Field(min_length=20, max_length=5000)
    description: str = Field(default="", max_length=2000)


# ---------- helpers ----------

def _row_to_project(row) -> dict:
    return {
        "id": row[0], "name": row[1], "slug": row[2], "idea_text": row[3],
        "description": row[4], "lifecycle_stage": row[5],
        "created_at": row[6], "updated_at": row[7],
    }


def _unique_slug(cur, owner_id: str, base: str) -> str:
    slug, n = base, 1
    while True:
        cur.execute(
            db_mod.q("SELECT 1 FROM projects WHERE owner_id = %s AND slug = %s"),
            (owner_id, slug),
        )
        if cur.fetchone() is None:
            return slug
        n += 1
        slug = f"{base}-{n}"


# ---------- auth ----------

@app.post("/api/auth/signup")
def signup(body: SignupIn):
    user = auth_mod.create_user(body.email, body.password, body.display_name)
    return {"user": user, "token": auth_mod.make_token(user["id"])}


@app.post("/api/auth/login")
def login(body: LoginIn):
    user = auth_mod.authenticate(body.email, body.password)
    return {"user": user, "token": auth_mod.make_token(user["id"])}


@app.get("/api/auth/me")
def me(user: dict = Depends(auth_mod.get_current_user)):
    return {"user": user}


# ---------- projects ----------

@app.get("/api/projects")
def list_projects(user: dict = Depends(auth_mod.get_current_user)):
    with db_mod.get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            db_mod.q(
                "SELECT id, name, slug, idea_text, description, lifecycle_stage,"
                " created_at, updated_at FROM projects"
                " WHERE owner_id = %s AND deleted_at IS NULL ORDER BY updated_at DESC"
            ),
            (user["id"],),
        )
        return {"projects": [_row_to_project(r) for r in cur.fetchall()]}


@app.post("/api/projects", status_code=201)
def create_project(body: ProjectIn, user: dict = Depends(auth_mod.get_current_user)):
    with db_mod.get_conn() as conn:
        cur = conn.cursor()
        slug = _unique_slug(cur, user["id"], _slugify(body.name))
        pid, now = db_mod.new_id(), db_mod.now_iso()
        cur.execute(
            db_mod.q(
                "INSERT INTO projects (id, owner_id, name, slug, idea_text, description,"
                " lifecycle_stage, created_at, updated_at)"
                " VALUES (%s, %s, %s, %s, %s, %s, 'idea', %s, %s)"
            ),
            (pid, user["id"], body.name.strip(), slug, body.idea_text.strip(),
             body.description.strip(), now, now),
        )
    log.info("project created: %s (%s)", pid, body.name.strip()[:60])
    return {"project": {
        "id": pid, "name": body.name.strip(), "slug": slug,
        "idea_text": body.idea_text.strip(), "description": body.description.strip(),
        "lifecycle_stage": "idea", "created_at": now, "updated_at": now,
    }}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str, user: dict = Depends(auth_mod.get_current_user)):
    with db_mod.get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            db_mod.q(
                "SELECT id, name, slug, idea_text, description, lifecycle_stage,"
                " created_at, updated_at FROM projects"
                " WHERE id = %s AND owner_id = %s AND deleted_at IS NULL"
            ),
            (project_id, user["id"]),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        project = _row_to_project(row)
        cur.execute(
            db_mod.q(
                "SELECT id, req_code, title, description, acceptance_criteria, category,"
                " verification_kind, status, origin, created_at FROM requirements"
                " WHERE project_id = %s ORDER BY req_code"
            ),
            (project_id,),
        )
        project["requirements"] = [
            {"id": r[0], "req_code": r[1], "title": r[2], "description": r[3],
             "acceptance_criteria": r[4], "category": r[5], "verification_kind": r[6],
             "status": r[7], "origin": r[8], "created_at": r[9]}
            for r in cur.fetchall()
        ]
    return {"project": project}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str, user: dict = Depends(auth_mod.get_current_user)):
    with db_mod.get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            db_mod.q(
                "UPDATE projects SET deleted_at = %s, updated_at = %s"
                " WHERE id = %s AND owner_id = %s AND deleted_at IS NULL"
            ),
            (db_mod.now_iso(), db_mod.now_iso(), project_id, user["id"]),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found.")
    return {"status": "deleted"}


@app.post("/api/projects/{project_id}/generate-requirements", status_code=201)
def api_generate_requirements(project_id: str, user: dict = Depends(auth_mod.get_current_user)):
    with db_mod.get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            db_mod.q("SELECT idea_text FROM projects WHERE id = %s AND owner_id = %s AND deleted_at IS NULL"),
            (project_id, user["id"]),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found.")
    reqs = generate_requirements(project_id, row[0], user["id"])
    return {"requirements": reqs}


# ---------- health ----------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "mommy-i-did-it",
        "version": "0.1.0",
        "db": "postgres" if db_mod.USE_POSTGRES else "sqlite-dev",
    }


# ---------- frontend ----------

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        # API routes are matched above; everything else serves the SPA.
        target = DIST / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(DIST / "index.html")
else:
    log.warning("frontend/dist not found — API-only mode. Build the frontend.")
