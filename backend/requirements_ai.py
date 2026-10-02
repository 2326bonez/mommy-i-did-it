"""AI requirement generation: IDEA -> structured REQ-### records."""
from __future__ import annotations

import json
import logging
import re

from fastapi import HTTPException

from db import get_conn, new_id, now_iso, q
from providers import Capability, ModelRequest, ProviderError, registry

log = logging.getLogger("mommy.requirements")

SYSTEM_PROMPT = """You are a senior product analyst for an app-building platform.
Given a user's app idea, produce a structured list of software requirements.

Return ONLY a JSON object with this exact shape:
{
  "requirements": [
    {
      "title": "Short requirement title",
      "description": "2-3 sentence description of what this requirement covers",
      "acceptance_criteria": "Concrete, testable criteria (what must be true when done)",
      "category": "one of: functional, ui, data, integration, security, performance",
      "verification_kind": "one of: ai, human, both"
    }
  ]
}

Rules:
- Generate 5 to 8 requirements. Cover the core value first.
- acceptance_criteria must be concrete and checkable, not vague.
- verification_kind: "ai" for machine-testable (logic, data, API), "human" for
  observable UX (looks right, feels right, audio/video playback), "both" when
  it needs both.
- No markdown, no commentary — JSON object only."""

VALID_CATEGORIES = {"functional", "ui", "data", "integration", "security", "performance"}
VALID_KINDS = {"ai", "human", "both"}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
    return slug or "project"


def generate_requirements(project_id: str, idea_text: str, owner_id: str) -> list[dict]:
    """Call the provider layer, validate, and persist requirements. Returns the rows."""
    # Ownership check
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            q("SELECT id FROM projects WHERE id = %s AND owner_id = %s AND deleted_at IS NULL"),
            (project_id, owner_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Project not found.")

    provider = registry.resolve(Capability.REASONING)
    try:
        resp = provider.complete(
            ModelRequest(
                capability=Capability.REASONING,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"App idea:\n\n{idea_text.strip()}",
                max_tokens=2500,
                temperature=0.7,
                json_mode=True,
            )
        )
    except ProviderError as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        data = json.loads(resp.text)
        raw_reqs = data["requirements"]
        if not isinstance(raw_reqs, list) or not raw_reqs:
            raise ValueError("empty requirements list")
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        log.error("AI returned unparseable requirements: %s", type(e).__name__)
        raise HTTPException(
            status_code=502,
            detail="The AI returned an invalid response. Please try again.",
        )

    # Per-project REQ-### sequencing
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q("SELECT COUNT(*) FROM requirements WHERE project_id = %s"), (project_id,))
        start_n = cur.fetchone()[0]

    rows: list[dict] = []
    now = now_iso()
    with get_conn() as conn:
        cur = conn.cursor()
        for i, r in enumerate(raw_reqs[:10], start=1):
            title = str(r.get("title", "")).strip()[:200] or f"Requirement {i}"
            description = str(r.get("description", "")).strip()[:2000]
            acceptance = str(r.get("acceptance_criteria", "")).strip()[:2000]
            category = str(r.get("category", "functional")).strip().lower()
            kind = str(r.get("verification_kind", "ai")).strip().lower()
            if category not in VALID_CATEGORIES:
                category = "functional"
            if kind not in VALID_KINDS:
                kind = "ai"
            req_code = f"REQ-{start_n + i:03d}"
            rid = new_id()
            cur.execute(
                q(
                    "INSERT INTO requirements (id, project_id, req_code, title, description,"
                    " acceptance_criteria, category, verification_kind, status, origin,"
                    " created_at, updated_at)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'draft', 'ai', %s, %s)"
                ),
                (rid, project_id, req_code, title, description, acceptance, category, kind, now, now),
            )
            rows.append(
                {
                    "id": rid,
                    "req_code": req_code,
                    "title": title,
                    "description": description,
                    "acceptance_criteria": acceptance,
                    "category": category,
                    "verification_kind": kind,
                    "status": "draft",
                    "origin": "ai",
                }
            )

    # Advance lifecycle to 'plan' once requirements exist
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            q("UPDATE projects SET lifecycle_stage = 'plan', updated_at = %s WHERE id = %s"),
            (now_iso(), project_id),
        )
    log.info(
        "generated %d requirements for project %s via %s/%s",
        len(rows), project_id, resp.provider, resp.model,
    )
    return rows
