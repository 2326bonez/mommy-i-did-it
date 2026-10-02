# Mommy I Did It — Platform Architecture

**Version:** 1.0 (Architecture Blueprint)
**Date:** October 1, 2026
**Status:** Build plan — not yet implemented

> "Build It. Tune It. Finish It."
> An AI-powered application-building platform where users genuinely build
> applications — real code, real files, real deployments — with honest
> verification, build protection, and full source ownership.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Tech Stack & Justification](#2-tech-stack--justification)
3. [Database Schema](#3-database-schema)
4. [API Design](#4-api-design)
5. [Agent System Design](#5-agent-system-design)
6. [Model Provider Layer](#6-model-provider-layer)
7. [Build Protection Design](#7-build-protection-design)
8. [Verification System Design](#8-verification-system-design)
9. [Connector Architecture](#9-connector-architecture)
10. [Source Generation & Export](#10-source-generation--export)
11. [Provenance Ledger](#11-provenance-ledger)
12. [Security Considerations](#12-security-considerations)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Phased Build Plan](#14-phased-build-plan)
15. [Open Questions & Risks](#15-open-questions--risks)

---

## 1. System Overview

### 1.1 What This Is

Mommy I Did It is a web platform where a non-technical (or technical) user
describes an application idea and, through a guided lifecycle, ends up with:

- **Real, runnable source code** (not a mockup, not a demo script)
- **A deployed application** they can visit in a browser
- **A downloadable source archive** they own outright
- **A verification record** proving what was built, tested, and verified
- **A release certificate** marking the achievement

### 1.2 The Lifecycle

```
IDEA → PLAN → BUILD → TEST → EVIDENCE → VERIFY → PROTECT → RELEASE → PUBLISH → OWN
```

Each stage has a concrete, machine-checkable definition:

| Stage     | Definition                                                        | Gate to Next Stage                              |
|-----------|-------------------------------------------------------------------|-------------------------------------------------|
| IDEA      | User describes what they want in plain language                   | Idea text ≥ 20 chars, project created            |
| PLAN      | AI generates requirements (REQ-###) with acceptance criteria      | ≥ 1 requirement approved by user                 |
| BUILD     | Agents generate real source files into the project workspace       | ≥ 1 source file committed to a version           |
| TEST      | Tests execute against the generated code (unit, integration, E2E) | ≥ 1 test run with recorded results              |
| EVIDENCE  | Test outputs, screenshots, logs attached to requirements           | Every REQ has ≥ 1 evidence record                |
| VERIFY    | AI verifies machine-testable REQs; human verifies observable REQs  | All REQs verified (PASS) or honestly BLOCKED     |
| PROTECT   | Version snapshot taken; regression baseline established            | Snapshot stored, rollback tested                 |
| RELEASE   | Release gate evaluates: all gates green, no unresolved conflicts  | Gate status = RELEASE READY                      |
| PUBLISH   | Deploy to hosting (Render) and/or generate public share link       | Deploy live, health check passing                |
| OWN       | Source archive + certificate + provenance ledger delivered to user | Export downloaded or confirmed                   |

**Critical rule:** stages are honest. If BUILD produced no runnable code, the
project cannot advance past BUILD. The UI shows the true stage, never a fake
green checkmark.

### 1.3 Core Architectural Principles

1. **Real over simulated.** Every feature is either REAL or explicitly labeled
   `SIMULATED` / `NOT YET IMPLEMENTED` / `PLATFORM BLOCKED`. Never present a
   simulation as real.
2. **No overrides.** AI cannot override a human verification. A human cannot
   override an AI verification. Conflicts remain visible with both pieces of
   evidence preserved.
3. **Evidence is version-bound.** If the implementation changes enough to
   invalidate prior evidence, new evidence is required. Stale evidence never
   silently certifies a changed implementation.
4. **The user owns the source.** At any point, the user can download the
   complete, runnable source. No lock-in.
5. **Build protection is automatic.** Every meaningful change creates a new
   version. The last known-good version is always recoverable.
6. **Agents are real executors, not narrative.** An agent run produces
   checkable artifacts (files, test results, evidence records) — not just a
   chat log saying "done."

### 1.4 High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        WEB FRONTEND (React SPA)                  │
│  Project Dashboard · Requirement Board · Agent Console ·         │
│  Verification Panel · Version Timeline · Release Center ·       │
│  Connector Manager · Source Export                               │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS / JSON
┌────────────────────────────▼────────────────────────────────────┐
│                     API SERVER (FastAPI, Python)                 │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │   Project &  │  │    Agent     │  │   Verification &      │  │
│  │ Requirement  │  │  Orchestrator │  │   Release Gate        │  │
│  │   Service    │  │              │  │                       │  │
│  └──────────────┘  └──────┬───────┘  └───────────────────────┘  │
│                          │                                      │
│  ┌──────────────┐  ┌─────▼────────┐  ┌───────────────────────┐  │
│  │    Model     │  │    Build     │  │   Connector           │  │
│  │   Provider   │◄─┤  Protection  │  │   Manager             │  │
│  │    Layer     │  │  (Versions)  │  │                       │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │    Source    │  │   Sandbox    │                              │
│  │  Generator   │─►│  Executor    │ (isolated codegen + tests)   │
│  └──────────────┘  └──────────────┘                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │  Neon     │  │  Object   │  │ External  │
        │ Postgres  │  │  Storage  │  │ Providers │
        │ (primary  │  │ (versions,│  │ (OpenAI,  │
        │  DB)      │  │  exports, │  │ Anthropic,│
        └───────────┘  │  certs)   │  │ GitHub…)  │
                       └───────────┘  └───────────┘
```

### 1.5 Key Design Decisions (Summary)

| Decision | Choice | Why |
|----------|--------|-----|
| Backend language | Python 3.12 + FastAPI | Team already ships FastAPI; async support; rich ecosystem for codegen/testing |
| Frontend | React 18 + Vite + TypeScript | Matches existing Bonez Labz apps; component ecosystem |
| Primary database | Neon Postgres | Already in use; serverless; branching useful for version snapshots |
| Version storage | Content-addressed file store (local disk → S3-compatible) | Git-like immutability without Git's complexity for non-dev users |
| AI providers | OpenAI + Anthropic via abstraction layer | No lock-in; BYOK supported |
| Sandboxed execution | Docker containers (one per project build) | Real test execution in isolation; reproducible |
| Deployment target | Render (primary) | Existing infrastructure; free tier friendly |
| Auth | Email + password (bcrypt) + sessions; Google OAuth later | Simple, matches other Bonez apps |

---

## 2. Tech Stack & Justification

### 2.1 Backend: Python 3.12 + FastAPI

- **Why Python:** The team's existing apps (ICU, Digitscoper) are FastAPI.
  Shared patterns for auth, Stripe, rate limiting transfer directly.
- **Why FastAPI:** Async endpoints for long-running agent executions
  (SSE streaming of agent progress). Pydantic validation. Auto-generated
  OpenAPI docs for the future public API.
- **Background work:** `arq` (async Redis queue) or Python `asyncio` tasks
  for agent runs. Start with in-process asyncio; move to `arq` + Redis when
  concurrent builds demand it.

### 2.2 Frontend: React 18 + Vite + TypeScript + Tailwind

- Matches Chef Suey's stack (React 18 + Vite 6 + Tailwind).
- Component library: shadcn/ui (already used in Digitscoper web).
- State: TanStack Query for server state; Zustand for UI state.
- Real-time agent progress: Server-Sent Events (SSE) from FastAPI.

### 2.3 Database: Neon Postgres (primary)

- Already provisioned and connected.
- **Branching** is a killer feature for Build Protection: each version
  snapshot can be a Neon branch, giving instant rollback at the DB level.
- Fallback: SQLite for local development only (`DATABASE_URL` unset →
  local SQLite with a loud warning banner, never silent).

### 2.4 AI: Model Provider Layer (OpenAI + Anthropic)

- Abstraction over both providers; agents request *capabilities*
  (`reasoning`, `codegen`, `review`), not model names.
- BYOK: users can supply their own API keys (encrypted at rest).
- Platform keys used when user has no key (metered).

### 2.5 Sandboxed Code Execution: Docker

- Each project gets an isolated container for: dependency install,
  test execution, build verification, screenshot capture (Playwright).
- Resource limits: CPU/memory caps per build; timeout kills.
- **Why not just subprocess:** generated code is untrusted. It must not
  touch the host, other projects, or secrets.

### 2.6 Object Storage: S3-Compatible (Render Disks → Cloudflare R2 later)

- Stores: version snapshots (tarballs), source exports (ZIPs), release
  packages, certificates (PDFs), evidence artifacts (screenshots, logs).
- Start: local disk on Render (with the known ephemerality caveat —
  documented, not hidden). Migrate to R2 before public launch.

### 2.7 Deployment: Render

- API server: Render Web Service (Python).
- Frontend: Render Static Site (Vite build).
- Consistent with all other Bonez Labz apps.

---

## 3. Database Schema

All tables use UUID primary keys (`gen_random_uuid()`), `created_at` /
`updated_at` timestamps (UTC), and soft-delete where user data is involved.

### 3.1 Identity & Access

```sql
-- Users of the platform
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,
    password_hash TEXT,                       -- NULL for OAuth-only
    display_name TEXT NOT NULL,
    tier        TEXT NOT NULL DEFAULT 'free'   -- free | pro | team | admin
                  CHECK (tier IN ('free','pro','team','admin')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- API keys users bring (BYOK) — encrypted, never displayed
CREATE TABLE user_provider_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider        TEXT NOT NULL,              -- 'openai' | 'anthropic'
    key_ciphertext  TEXT NOT NULL,              -- Fernet-encrypted
    key_fingerprint TEXT NOT NULL,              -- last 4 chars for identification
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, provider)
);

-- Platform-issued API keys for programmatic access (Pro+)
CREATE TABLE api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash    TEXT NOT NULL UNIQUE,          -- SHA-256 of the key
    key_prefix  TEXT NOT NULL,                 -- e.g. 'mdi_live_a1b2' (for identification)
    name        TEXT NOT NULL,
    last_used_at TIMESTAMPTZ,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.2 Projects & Requirements

```sql
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID NOT NULL REFERENCES users(id),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,              -- URL-safe, unique per owner
    idea_text       TEXT NOT NULL,              -- the original IDEA
    description     TEXT,
    lifecycle_stage TEXT NOT NULL DEFAULT 'idea'
        CHECK (lifecycle_stage IN (
            'idea','plan','build','test','evidence',
            'verify','protect','release','publish','own'
        )),
    current_version_id UUID,                    -- FK to versions (set after first snapshot)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE (owner_id, slug)
);

CREATE TABLE requirements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    req_code        TEXT NOT NULL,              -- 'REQ-001' (per-project sequence)
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,         -- machine-testable where possible
    category        TEXT NOT NULL DEFAULT 'functional',
    verification_kind TEXT NOT NULL DEFAULT 'ai'
        CHECK (verification_kind IN ('ai','human','both')),
    status          TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','approved','in_progress','implemented',
                          'verified','blocked','failed')),
    origin          TEXT NOT NULL DEFAULT 'ai' -- 'ai' | 'human' | 'imported'
        CHECK (origin IN ('ai','human','imported')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, req_code)
);
```

### 3.3 Agent System

```sql
-- Agent type registry (what agents exist and what they can do)
CREATE TABLE agent_types (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT NOT NULL UNIQUE,     -- 'lead_builder', 'frontend', ...
    display_name    TEXT NOT NULL,
    description     TEXT NOT NULL,
    responsibilities TEXT NOT NULL,           -- human-readable
    allowed_tools   JSONB NOT NULL DEFAULT '[]',
    -- e.g. ["write_file","run_tests","read_file","web_search"]
    required_capabilities JSONB NOT NULL DEFAULT '[]',
    -- e.g. ["codegen","reasoning"]
    is_real         BOOLEAN NOT NULL DEFAULT TRUE,
    -- FALSE → UI must label SIMULATED
    max_parallel    INT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A single execution of an agent (one "run")
CREATE TABLE agent_executions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_type_id   UUID NOT NULL REFERENCES agent_types(id),
    version_id      UUID,                       -- version this run contributed to
    trigger         TEXT NOT NULL,              -- 'user' | 'lead_builder' | 'schedule' | 'retry'
    status          TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued','running','succeeded','failed',
                          'cancelled','awaiting_human')),
    input_summary   TEXT NOT NULL,              -- what it was asked to do
    model_provider  TEXT,                       -- 'openai' | 'anthropic' | NULL if simulated
    model_name      TEXT,                       -- resolved model, e.g. 'gpt-4o'
    capability_used TEXT,                       -- 'codegen' | 'reasoning' | ...
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    tokens_in       INT DEFAULT 0,
    tokens_out      INT DEFAULT 0,
    cost_credits    NUMERIC(10,4) DEFAULT 0,    -- build credits consumed
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Individual tool calls within an execution (the audit trail)
CREATE TABLE agent_tool_calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id    UUID NOT NULL REFERENCES agent_executions(id) ON DELETE CASCADE,
    seq             INT NOT NULL,               -- ordering within the execution
    tool_name       TEXT NOT NULL,              -- 'write_file', 'run_tests', ...
    arguments       JSONB NOT NULL,             -- sanitized (no secrets)
    result_summary  TEXT,                       -- human-readable outcome
    result_artifact_id UUID,                    -- FK to artifacts if it produced one
    status          TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok','error')),
    duration_ms     INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (execution_id, seq)
);

-- Files, screenshots, logs, zips produced by agents or the system
CREATE TABLE artifacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    execution_id    UUID REFERENCES agent_executions(id) ON DELETE SET NULL,
    kind            TEXT NOT NULL
        CHECK (kind IN ('source_file','test_report','screenshot','log',
                        'evidence','release_package','certificate','export')),
    path            TEXT NOT NULL,              -- storage path
    filename        TEXT NOT NULL,
    mime_type       TEXT,
    size_bytes      BIGINT,
    sha256          TEXT NOT NULL,              -- integrity
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.4 Versions & Build Protection

```sql
-- Immutable snapshot of the project's source at a point in time
CREATE TABLE versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_number  INT NOT NULL,               -- 1, 2, 3... per project
    parent_version_id UUID REFERENCES versions(id),
    snapshot_path   TEXT NOT NULL,              -- tarball in object storage
    snapshot_sha256 TEXT NOT NULL,
    file_manifest   JSONB NOT NULL,             -- [{path, sha256, size}]
    created_by      TEXT NOT NULL               -- 'user' | 'agent:<slug>' | 'system'
        CHECK (created_by LIKE 'user' OR created_by LIKE 'agent:%'
               OR created_by = 'system'),
    change_summary  TEXT NOT NULL,
    is_known_good   BOOLEAN NOT NULL DEFAULT FALSE,
    regression_status TEXT NOT NULL DEFAULT 'not_checked'
        CHECK (regression_status IN (
            'not_checked','checking','passed','failed')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, version_number)
);

-- Regression check results (comparing a version against its baseline)
CREATE TABLE regression_checks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id      UUID NOT NULL REFERENCES versions(id) ON DELETE CASCADE,
    baseline_version_id UUID NOT NULL REFERENCES versions(id),
    status          TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running','passed','failed','error')),
    -- Per-requirement results: did previously-passing REQs still pass?
    results         JSONB NOT NULL DEFAULT '[]',
    -- [{req_code, baseline: 'pass', current: 'pass'|'fail', detail}]
    summary         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ
);
```

### 3.5 Verification & Evidence

```sql
-- Evidence attached to a requirement (test output, screenshot, log, human note)
CREATE TABLE evidence (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id  UUID NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    version_id      UUID NOT NULL REFERENCES versions(id),
    -- evidence is BOUND to the version it was collected against
    kind            TEXT NOT NULL
        CHECK (kind IN ('test_result','screenshot','log','human_observation',
                        'code_review','external_check')),
    title           TEXT NOT NULL,
    body            TEXT,                       -- notes / observation text
    artifact_id     UUID REFERENCES artifacts(id),
    submitted_by    TEXT NOT NULL               -- 'ai:<execution_id>' | 'human:<user_id>'
        CHECK (submitted_by LIKE 'ai:%' OR submitted_by LIKE 'human:%'),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A verification verdict on a requirement
CREATE TABLE verifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id  UUID NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    version_id      UUID NOT NULL REFERENCES versions(id),
    verifier_kind   TEXT NOT NULL CHECK (verifier_kind IN ('ai','human')),
    verifier_ref    TEXT NOT NULL,              -- execution_id or user_id
    verdict         TEXT NOT NULL
        CHECK (verdict IN ('pass','fail','blocked','needs_info')),
    rationale       TEXT NOT NULL,              -- required, no empty verdicts
    evidence_ids    UUID[] NOT NULL DEFAULT '{}',
    -- For 'blocked': what is blocking (e.g. 'needs human: no audio device')
    blocked_reason  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- One active verdict per (requirement, version, verifier_kind).
    -- New verdicts supersede; old ones are preserved (audit trail).
    superseded_by   UUID REFERENCES verifications(id)
);

-- When AI and human disagree (or both required and one is missing)
CREATE TABLE verification_conflicts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id  UUID NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    version_id      UUID NOT NULL REFERENCES versions(id),
    ai_verdict      TEXT NOT NULL,
    human_verdict   TEXT,                       -- NULL if human hasn't weighed in
    status          TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','acknowledged','resolved_by_evidence')),
    -- NOTE: 'resolved' never means "someone overrode."
    -- It means new evidence satisfied both sides.
    resolution_note TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);
```

**No-override enforcement (application logic + DB constraints):**

- `verifications` rows are INSERT-only. There is no UPDATE path in the API.
  A new verdict INSERTs a row and sets `superseded_by` on the old row.
- Only the original verifier kind can supersede its own verdict
  (AI supersedes AI; human supersedes human). The API rejects cross-kind
  supersession with 403.
- `verification_conflicts.status` can never transition to a state meaning
  "overridden." Resolution requires new evidence IDs linked to the conflict.

### 3.6 Connectors

```sql
CREATE TABLE connector_types (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT NOT NULL UNIQUE,     -- 'github', 'vercel', 'stripe', ...
    display_name    TEXT NOT NULL,
    category        TEXT NOT NULL,              -- 'git' | 'hosting' | 'payments' | ...
    auth_scheme     TEXT NOT NULL               -- 'oauth2' | 'api_key' | 'none'
        CHECK (auth_scheme IN ('oauth2','api_key','none')),
    capabilities    JSONB NOT NULL DEFAULT '[]', -- ['deploy','commit','charge',...]
    is_available    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-user connector instance
CREATE TABLE connectors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connector_type_id UUID NOT NULL REFERENCES connector_types(id),
    status          TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available','connecting','connected','authorized',
                          'executable','error','degraded','disconnected',
                          'not_supported')),
    -- 'connected' ≠ 'working'. 'executable' means a capability probe succeeded.
    credential_ciphertext TEXT,                -- encrypted OAuth token / API key
    last_probe_at   TIMESTAMPTZ,
    last_probe_result JSONB,                    -- {capability: 'ok'|'fail', ...}
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, connector_type_id)
);

-- Every connector action is logged (idempotency + audit)
CREATE TABLE connector_actions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_id    UUID NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
    project_id      UUID REFERENCES projects(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,              -- 'deploy', 'commit', 'charge', ...
    idempotency_key TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'started'
        CHECK (status IN ('started','succeeded','failed')),
    request_summary JSONB,                      -- sanitized
    result_summary  JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (connector_id, idempotency_key)
);
```

### 3.7 Releases, Publishing, Certificates

```sql
-- Release gate evaluation for a version
CREATE TABLE release_gates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_id      UUID NOT NULL REFERENCES versions(id),
    status          TEXT NOT NULL DEFAULT 'evaluating'
        CHECK (status IN ('evaluating','built','tested','verified',
                          'release_ready','published','blocked')),
    -- Per-check results; ALL must pass for release_ready
    checks          JSONB NOT NULL DEFAULT '[]',
    -- [{check: 'all_reqs_verified', status: 'pass'|'fail', detail}, ...]
    evaluated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE releases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_id      UUID NOT NULL REFERENCES versions(id),
    release_gate_id UUID NOT NULL REFERENCES release_gates(id),
    release_number  TEXT NOT NULL,              -- 'v1.0.0' (per-project sequence)
    status          TEXT NOT NULL DEFAULT 'ready'
        CHECK (status IN ('ready','publishing','published','failed')),
    package_artifact_id UUID REFERENCES artifacts(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, release_number)
);

-- Deployment records (publishing)
CREATE TABLE deployments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    release_id      UUID NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    connector_id    UUID REFERENCES connectors(id),  -- e.g. Render/Vercel connector
    target          TEXT NOT NULL,              -- 'render' | 'share_link' | ...
    url             TEXT,
    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','deploying','live','failed')),
    health_check    JSONB,                      -- last health check result
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE certificates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    release_id      UUID NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    certificate_uid TEXT NOT NULL UNIQUE,      -- e.g. 'MDI-2026-XXXXXX'
    creator_name    TEXT NOT NULL,
    app_name        TEXT NOT NULL,
    release_number  TEXT NOT NULL,
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    pdf_artifact_id UUID REFERENCES artifacts(id),
    -- Revocation (e.g. if the release is later found to be fraudulent)
    revoked_at      TIMESTAMPTZ,
    revoke_reason   TEXT
);
```

### 3.8 Provenance Ledger

```sql
-- Every significant contribution to the project, classified by origin
CREATE TABLE provenance_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_id      UUID REFERENCES versions(id),
    origin          TEXT NOT NULL
        CHECK (origin IN ('human','ai','third_party','platform')),
    -- human: the user wrote/supplied it
    -- ai: an agent generated it (execution_id in ref)
    -- third_party: library, template, API, starter code
    -- platform: Mommy I Did It scaffolding (build scripts, default config)
    kind            TEXT NOT NULL,              -- 'code' | 'idea' | 'requirement' |
                                                -- 'test' | 'asset' | 'config' | 'doc'
    summary         TEXT NOT NULL,              -- "Generated React login form"
    ref             TEXT,                       -- execution_id, artifact path, npm package
    actor           TEXT,                       -- user_id, agent slug, or package name
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.9 Build Credits

```sql
CREATE TABLE credit_ledger (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delta           NUMERIC(10,4) NOT NULL,    -- +grant | -spend
    balance_after   NUMERIC(10,4) NOT NULL,
    reason          TEXT NOT NULL,              -- 'monthly_grant' | 'agent_run:<id>' |
                                                -- 'regression_recovery' | 'purchase'
    ref_id          UUID,                       -- agent_execution_id etc.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Credit rules (hard requirements):**
- Every credit spend links to a `ref_id`. No unattributed burns.
- Platform-caused regressions (Build Protection recovery) are credited back
  (`reason = 'regression_recovery'`) — users never pay for platform damage.
- Free tier: monthly grant sufficient for meaningful building (exact numbers
  set after measuring real token costs; no hard-coded pricing in code —
  configurable via `platform_config` table).

---

## 4. API Design

Base path: `/api/v1`. Auth: session cookie (web) or `Authorization: Bearer
<mdi_api_key>` (programmatic). All mutating endpoints are idempotency-aware
where it matters (connector actions, deployments).

### 4.1 Auth & Users

```
POST   /api/v1/auth/signup                  {email, password, display_name}
POST   /api/v1/auth/login                   {email, password}
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
POST   /api/v1/auth/provider-keys           {provider, api_key}      # BYOK
DELETE /api/v1/auth/provider-keys/{provider}
GET    /api/v1/users/me/credits
GET    /api/v1/users/me/credit-history
```

### 4.2 Projects

```
POST   /api/v1/projects                     {name, idea_text, description?}
GET    /api/v1/projects                     # list own projects
GET    /api/v1/projects/{id}
PATCH  /api/v1/projects/{id}                {name?, description?}
DELETE /api/v1/projects/{id}                # soft delete
GET    /api/v1/projects/{id}/timeline       # lifecycle event feed
```

### 4.3 Requirements

```
POST   /api/v1/projects/{id}/requirements/generate        # AI generates REQs from idea
GET    /api/v1/projects/{id}/requirements
POST   /api/v1/projects/{id}/requirements                 # human adds one
PATCH  /api/v1/requirements/{req_id}                      # edit / approve
POST   /api/v1/requirements/{req_id}/approve
POST   /api/v1/requirements/{req_id}/block    {reason}     # honest BLOCKED
```

### 4.4 Agents

```
GET    /api/v1/agent-types                              # registry; is_real flags
POST   /api/v1/projects/{id}/agent-runs                 # dispatch an agent
         {agent_slug, task, input_refs?}
GET    /api/v1/projects/{id}/agent-runs
GET    /api/v1/agent-runs/{exec_id}                     # status + progress (SSE optional)
GET    /api/v1/agent-runs/{exec_id}/events              # SSE stream of tool calls
POST   /api/v1/agent-runs/{exec_id}/cancel
GET    /api/v1/agent-runs/{exec_id}/tool-calls
```

**SSE event format** (agent progress):
```
event: tool_call
data: {"seq": 3, "tool": "write_file", "summary": "Created src/App.tsx"}

event: status
data: {"status": "running", "detail": "Running tests..."}

event: done
data: {"status": "succeeded", "version_id": "uuid..."}
```

### 4.5 Versions & Build Protection

```
POST   /api/v1/projects/{id}/versions/snapshot
         {change_summary}                               # manual snapshot
GET    /api/v1/projects/{id}/versions
GET    /api/v1/versions/{version_id}                    # manifest + metadata
GET    /api/v1/versions/{version_id}/diff/{other_id}    # file-level diff
POST   /api/v1/versions/{version_id}/restore            # rollback → creates NEW version
GET    /api/v1/versions/{version_id}/regression         # regression check results
POST   /api/v1/versions/{version_id}/regression/run     # trigger check
```

### 4.6 Evidence & Verification

```
POST   /api/v1/requirements/{req_id}/evidence
         {version_id, kind, title, body?, artifact_id?}
GET    /api/v1/requirements/{req_id}/evidence
POST   /api/v1/requirements/{req_id}/verifications      # AI path (system-called)
         {version_id, verdict, rationale, evidence_ids[]}
POST   /api/v1/requirements/{req_id}/verifications/human
         {version_id, verdict, rationale, evidence_ids[], blocked_reason?}
GET    /api/v1/requirements/{req_id}/verifications     # full history incl. superseded
GET    /api/v1/projects/{id}/conflicts
POST   /api/v1/conflicts/{conflict_id}/acknowledge
POST   /api/v1/conflicts/{conflict_id}/resolve         # requires new evidence_ids
```

### 4.7 Connectors

```
GET    /api/v1/connector-types
GET    /api/v1/connectors                               # user's connectors + statuses
POST   /api/v1/connectors/{type_slug}/connect           # starts OAuth / key flow
POST   /api/v1/connectors/{type_slug}/api-key          {api_key}  # key-based
POST   /api/v1/connectors/{id}/probe                   # capability check
DELETE /api/v1/connectors/{id}                         # disconnect
POST   /api/v1/connectors/{id}/actions                 # execute capability
         {action, params, idempotency_key}
```

### 4.8 Release, Publish, Export

```
GET    /api/v1/projects/{id}/release-gate              # current gate status + checks
POST   /api/v1/projects/{id}/release-gate/evaluate     # re-run evaluation
POST   /api/v1/projects/{id}/releases                  # create release (gate must be ready)
GET    /api/v1/releases/{release_id}
POST   /api/v1/releases/{release_id}/deploy            # publish via connector
         {connector_id | target: 'render'|'share_link'}
GET    /api/v1/releases/{release_id}/certificate       # download PDF
GET    /api/v1/projects/{id}/export/source             # download full source ZIP
GET    /api/v1/projects/{id}/export/release-package   # download proof ZIP
GET    /api/v1/projects/{id}/provenance                # provenance ledger
```

### 4.9 Error Format

```json
{
  "error": {
    "code": "VERIFICATION_CONFLICT",
    "message": "AI and human verifications disagree on REQ-003.",
    "details": {"conflict_id": "uuid...", "ai_verdict": "pass", "human_verdict": "fail"},
    "request_id": "req_..."
  }
}
```

Standard codes: `VALIDATION_ERROR`, `NOT_FOUND`, `FORBIDDEN`,
`INSUFFICIENT_CREDITS`, `VERIFICATION_CONFLICT`, `GATE_BLOCKED`,
`VERSION_STALE`, `CONNECTOR_ERROR`, `RATE_LIMITED`.

---

## 5. Agent System Design

### 5.1 Agent Registry (Seed Data)

| Slug | Display Name | Real? | Responsibilities | Tools | Capabilities |
|------|-------------|-------|------------------|-------|--------------|
| `lead_builder` | Lead Builder | ✅ | Decompose requirements into build tasks; dispatch specialist agents; integrate outputs | `dispatch_agent`, `read_file`, `write_file` | `reasoning`, `codegen` |
| `frontend` | Frontend Agent | ✅ | Generate UI code (React/Vite/Tailwind); components, pages, styles | `write_file`, `read_file`, `run_tests` | `codegen` |
| `backend` | Backend Builder | ✅ | Generate API code (FastAPI/Express); routes, models, middleware | `write_file`, `read_file`, `run_tests` | `codegen` |
| `database` | Database Agent | ✅ | Design schema; write migrations; seed data | `write_file`, `run_sql`, `read_file` | `codegen`, `reasoning` |
| `tester` | Testing Agent | ✅ | Write and execute tests; report results as evidence | `write_file`, `run_tests`, `run_shell` | `codegen`, `reasoning` |
| `security` | Security Agent | ✅ | Scan for secrets, injection risks, auth gaps; produce findings | `scan_secrets`, `read_file`, `run_tests` | `reasoning` |
| `debugger` | Debugger | ✅ | Diagnose failing tests/builds; propose minimal fixes | `read_file`, `run_tests`, `run_shell` | `reasoning`, `codegen` |
| `docs` | Documentation Agent | ✅ | Write README, API docs, user guides | `write_file`, `read_file` | `codegen` |
| `release` | Release Agent | ✅ | Evaluate release gate; assemble package; issue certificate | `evaluate_gate`, `build_package` | `reasoning` |
| `deployer` | Deployment Agent | ✅ | Deploy via connectors; health-check; report URL | `connector_action`, `http_check` | `reasoning` |
| `architect` | Architect | 🔶 Phase 2 | System design, tech decisions, ADRs | `write_file`, `read_file` | `reasoning` |
| `qa` | QA Agent | 🔶 Phase 2 | Human-like UI walkthrough via Playwright; screenshots | `browse_app`, `screenshot` | `reasoning` |

> Agents marked 🔶 ship as `is_real = FALSE` (labeled SIMULATED) until
> implemented. The UI renders simulated agents distinctly — never as if
> they executed.

### 5.2 Execution Model

```
User (or Lead Builder) dispatches agent
        │
        ▼
┌──────────────────┐
│  Orchestrator    │  1. Check credits (reserve estimate)
│                  │  2. Check agent permissions for project
│                  │  3. Resolve capability → model via Provider Layer
│                  │  4. Create agent_executions row (status=queued)
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Sandbox         │  5. Provision isolated workspace (project files @ version)
│  Provisioner     │     (Docker container, resource limits)
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Agent Loop      │  6. System prompt (role, tools, constraints)
│  (LLM + tools)   │  7. Tool calls execute in sandbox; each logged to
└────────┬─────────┘     agent_tool_calls with sanitized args
         ▼
┌──────────────────┐
│  Finalize        │  8. Collect file changes → create new version snapshot
│                  │  9. Record token usage → deduct credits (exact, not estimate)
│                  │ 10. Emit SSE 'done'; update execution status
└──────────────────┘
```

### 5.3 Tool Definitions

Each tool has a strict JSON schema, a permission scope, and a sandbox
implementation. Core tools:

| Tool | Description | Args | Returns |
|------|-------------|------|---------|
| `write_file` | Write/update a file in the project workspace | `path`, `content` | `{sha256, bytes}` |
| `read_file` | Read a file | `path` | `{content}` |
| `list_files` | List workspace files | `pattern?` | `{files[]}` |
| `run_tests` | Execute test suite in sandbox | `target?` | `{passed, failed, output, duration_ms}` |
| `run_shell` | Run allowlisted shell command | `command` | `{exit_code, stdout, stderr}` |
| `run_sql` | Execute SQL against project DB branch | `sql` | `{rows, rowcount}` |
| `dispatch_agent` | Lead Builder spawns a specialist | `agent_slug`, `task` | `{execution_id}` |
| `scan_secrets` | Scan workspace for leaked secrets | — | `{findings[]}` |
| `screenshot` | Capture app screenshot via Playwright | `url`, `viewport?` | `{artifact_id}` |
| `http_check` | Health-check a URL | `url` | `{status, latency_ms}` |

**Security rules:**
- `run_shell` allowlist: `npm`, `pip`, `pytest`, `node`, `python`, etc.
  No `curl` to arbitrary hosts (except allowlisted registries),
  no `ssh`, no `nc`.
- `write_file` cannot write outside the workspace root (path traversal
  rejected). Cannot write to `.env`, `*secret*`, `*credential*` paths.
- All tool args are sanitized before storage (no secrets in
  `agent_tool_calls.arguments`).

### 5.4 Agent Prompts & Honesty

- System prompts include an **honesty clause**: "If you cannot complete
  the task, say so explicitly. Never claim to have done work you did not
  do. Your tool calls are the evidence of your work."
- The orchestrator cross-checks: if an agent claims "tests pass" but no
  `run_tests` tool call exists in the execution, the execution is flagged
  `suspicious` and blocked from advancing the lifecycle.

### 5.5 Human-in-the-Loop

- Agents can set status `awaiting_human` with a structured question
  (e.g., "Which auth provider should I use? [Google] [GitHub] [Email]").
- The frontend renders these as decision cards. The user's choice resumes
  the execution.
- Human decisions are recorded in the audit trail and provenance ledger.

---

## 6. Model Provider Layer

### 6.1 Design

```python
# Conceptual interface (not literal code)

class Capability(str, Enum):
    REASONING = "reasoning"      # planning, review, debugging analysis
    CODEGEN   = "codegen"        # writing source files
    VISION    = "vision"         # screenshot analysis (Phase 2)
    EMBEDDING = "embedding"      # semantic search over project (Phase 2)

@dataclass
class ModelRequest:
    capability: Capability
    messages: list[Message]      # provider-agnostic format
    tools: list[ToolDef]         # provider-agnostic; adapted per provider
    max_tokens: int
    temperature: float
    user_id: UUID                # for BYOK resolution + metering

class ModelProvider(ABC):
    @abstractmethod
    async def complete(self, req: ModelRequest) -> ModelResponse: ...
    @abstractmethod
    def supports(self, cap: Capability) -> bool: ...

class ProviderRegistry:
    def resolve(self, capability, user_id) -> ModelProvider:
        # 1. If user has BYOK key for a provider supporting the capability → use it
        # 2. Else use platform key for the default provider for that capability
        # 3. Record which provider+model was used (for provenance + cost)
```

### 6.2 Provider Matrix (Initial)

| Capability | OpenAI (default) | Anthropic (default) | Notes |
|------------|------------------|---------------------|-------|
| `reasoning` | gpt-4o | claude-sonnet-4 | Configurable per deployment |
| `codegen` | gpt-4o | claude-sonnet-4 | Benchmark per task type; allow override |
| `vision` | gpt-4o | claude-sonnet-4 | Phase 2 |

Model names live in `platform_config`, **not** hard-coded. An admin can
swap `codegen` from OpenAI to Anthropic without a code deploy.

### 6.3 BYOK Flow

1. User adds key via `POST /api/v1/auth/provider-keys` (stored Fernet-encrypted).
2. On agent dispatch, registry checks `user_provider_keys` for an active key
   for a provider supporting the needed capability.
3. If found: the user's key is used; usage is attributed to the user
   (their provider bill, not platform credits for tokens — only a small
   platform orchestration fee, if any).
4. UI clearly shows per-execution: "Tokens billed to your OpenAI key" vs
   "Tokens billed to platform credits."
5. Keys are never returned by any API. Only `key_fingerprint` (last 4) is shown.

### 6.4 Anti-Self-Certification

The model that generated code **cannot** be the sole verifier of that code:
- AI verification of a requirement must use a *different* execution from
  the one that implemented it (enforced by `execution_id` comparison).
- Ideally a different capability path (e.g., implementation via `codegen`,
  verification via `reasoning` with a review-focused prompt).
- The verification prompt never sees "this is correct" — it sees the
  requirement, the code diff, and the test results, and must reach its own
  verdict.

---

## 7. Build Protection Design

### 7.1 Versioning

- **Every** agent execution that modifies files produces a new `versions`
  row with a content-addressed tarball (`sha256`).
- `file_manifest` records every file's hash — the version is fully
  described and reproducible.
- Versions are **immutable**. "Restore" creates a *new* version whose
  content equals the target (never rewrites history).

### 7.2 Known-Good Tracking

- A version becomes `is_known_good = TRUE` when:
  1. Its regression check passes against the previous known-good, AND
  2. All requirements that were `verified` on the previous known-good
     are still `verified` (or re-verified) on this version.
- The project's `current_version_id` always points at the latest version;
  a separate `last_known_good_version_id` (on `projects`) is the rollback target.

### 7.3 Regression Detection

Triggered automatically after each new version (async, non-blocking):

```
For each requirement that was 'verified' on baseline (last known-good):
    Re-run its linked tests against the new version (in sandbox)
    Compare verdicts:
        baseline pass → new pass   : OK
        baseline pass → new fail   : REGRESSION (flag it)
        baseline pass → new error  : REGRESSION (flag it)
Write regression_checks row with per-REQ results.
If any regression:
    - Mark version.regression_status = 'failed'
    - Notify user (dashboard banner + optional email)
    - Offer one-click rollback (creates new version from last known-good)
    - Do NOT auto-rollback (user decides; auto-rollback could destroy
      intentional breaking changes mid-refactor)
```

### 7.4 Rollback

`POST /api/v1/versions/{id}/restore`:
1. Verifies the target version belongs to the project.
2. Creates a **new** version with the target's file manifest
   (`change_summary = "Rollback to v{N}"`, `parent_version_id` = current).
3. Runs the regression check against last known-good.
4. Updates `projects.current_version_id`.
5. Records provenance entry (`origin='human'`, `kind='config'`).

### 7.5 Platform-Caused Recovery (Credit Protection)

If a regression is traced to platform action (failed deploy script,
provider outage mid-build, orchestrator bug):
1. `regression_checks` records `cause = 'platform'`.
2. A `credit_ledger` entry refunds the credits consumed by the failed
   version's agent executions (`reason='regression_recovery'`).
3. The user sees: "We broke this — here's your credits back, and your
   last good version is one click away."

---

## 8. Verification System Design

### 8.1 Requirement Verification Kinds

Each requirement declares `verification_kind` at PLAN time:

- **`ai`**: machine-testable (e.g., "Login rejects wrong password").
  AI runs/reads tests and issues a verdict.
- **`human`**: human-observable (e.g., "Audio progress bar moves smoothly").
  Only a human can verify. AI may attach supporting evidence but cannot
  issue the verdict.
- **`both`**: needs both (e.g., "Checkout completes and confirmation
  email looks correct" — AI checks the transaction, human checks the email).

### 8.2 Evidence Rules

- Evidence is **bound to a version** (`evidence.version_id`). If the code
  changes (new version), old evidence is marked `stale` for the new version.
- A verification verdict must cite ≥ 1 evidence ID. Empty verdicts are
  rejected (DB `NOT NULL` + API validation).
- **Trivial-evidence filter** (server-side, actually enforced):
  - Minimum 15 characters for text evidence.
  - Blocklist of vacuous phrases ("it works", "looks good", "tested ok",
    case-insensitive, with and without punctuation).
  - For `test_result` evidence: must reference an actual test run
    (`artifact_id` → test report with ≥ 1 assertion).
  - For `screenshot` evidence: must be a real captured image (not a
    placeholder; checked via dimensions + perceptual hash against
    known placeholders).
- Relevance check (Phase 2, ML-assisted): evidence should relate to the
  requirement text. Phase 1: the *human* UI warns when linking evidence
  whose title doesn't share keywords with the requirement.

### 8.3 The No-Override Rule (Implementation)

```
AI wants to change a human verdict:
    → API returns 403 CANNOT_SUPERSEDE_OTHER_KIND
    → System creates/updates verification_conflicts row
    → Both verdicts remain visible

Human wants to change an AI verdict:
    → Same 403. Same conflict flow.

Conflict resolution (the ONLY path):
    1. New evidence is submitted (new version, new test, new observation)
    2. The disagreeing party issues a NEW verdict citing the new evidence
    3. If verdicts now agree → conflict status = 'resolved_by_evidence'
    4. The old disagreeing verdict is preserved (superseded_by link)
```

### 8.4 Stale Evidence Invalidation

When a new version is created:
- All `verifications` tied to older versions remain in history but are
  marked `stale_for_version = <new_version_id>` (computed, not stored —
  derived by comparing `verifications.version_id` to current).
- The release gate's `all_reqs_verified` check only counts verifications
  where `version_id` = the candidate release version (or a version whose
  file manifest is identical for the relevant files — Phase 2 optimization;
  Phase 1: exact version match required).
- The UI shows: "REQ-003 was verified on v4, but you're on v7 —
  re-verification needed." One click re-runs AI verification; human
  re-verification is a deliberate action.

### 8.5 Release Gate Checks

The gate evaluates these checks; **all** must pass for `release_ready`:

| Check | What It Verifies |
|-------|------------------|
| `all_reqs_verified` | Every approved REQ has a current (non-stale) `pass` verdict |
| `no_open_conflicts` | Zero `verification_conflicts` with status `open` |
| `no_failed_regression` | Latest version's regression check ≠ `failed` |
| `tests_passing` | Latest test run on the version: 0 failures |
| `no_secrets_leaked` | Security Agent's latest scan: 0 findings |
| `evidence_complete` | Every REQ has ≥ 1 non-stale evidence record |
| `human_verifs_done` | All `human`/`both` REQs have human verdicts |

If any check fails, the gate returns `blocked` with the specific failing
checks and remediation hints. The gate **never** issues `release_ready`
based on subscription tier or payment status.

---

## 9. Connector Architecture

### 9.1 State Machine

```
AVAILABLE ──connect()──► CONNECTING ──success──► CONNECTED
    ▲                         │                      │
    │                         │ fail                 │ authorize()
    │                         ▼                      ▼
    │                       ERROR ──retry──► CONNECTING
    │                         │                AUTHORIZED ──probe()──► EXECUTABLE
    └──── disconnect() ───────┴───◄── degraded() ──┘
                                   │
                              DEGRADED (partial capability failure)
```

- `CONNECTED` = credential stored and basic auth succeeded.
- `AUTHORIZED` = required scopes/permissions confirmed.
- `EXECUTABLE` = a live capability probe succeeded (e.g., test deploy
  to a scratch target, test commit to a scratch repo).
- The UI **never** shows "Connected ✓" as if it means working. It shows
  the precise state and the last probe result per capability.

### 9.2 Initial Connector Catalog

| Slug | Category | Auth | Capabilities (Phase 1) |
|------|----------|------|------------------------|
| `github` | git | OAuth2 | `commit`, `push`, `create_repo` |
| `render` | hosting | API key | `deploy`, `health_check`, `logs` |
| `vercel` | hosting | OAuth2 | `deploy`, `health_check` (Phase 2) |
| `stripe` | payments | API key (restricted) | `create_price`, `webhook_status` (Phase 2) |
| `neon` | database | API key | `branch`, `connection_string` (Phase 2) |

### 9.3 Idempotency

Every `connector_actions` row carries an `idempotency_key` (client-generated
UUID). Retrying with the same key returns the original result instead of
executing twice. Unique constraint on `(connector_id, idempotency_key)`
enforces this at the DB level.

### 9.4 Secrets Handling

- OAuth tokens and API keys are Fernet-encrypted (`credential_ciphertext`).
- The encryption key lives in the platform's secret store (Render env var),
  **never** in the database or code.
- Connector probes and actions run server-side; the browser never sees
  raw credentials.

---

## 10. Source Generation & Export

### 10.1 How Real Code Gets Generated

This is the core differentiator from the Base44 prototype. The pipeline:

```
Requirement (REQ-###)
    │
    ▼
Lead Builder decomposes → build tasks per agent
    │
    ▼
Specialist agents generate files via Model Provider Layer
    │  (system prompts include target stack, file conventions,
    │   and "generate complete, runnable code — no TODOs, no stubs")
    ▼
Files written to sandbox workspace (Docker)
    │
    ▼
Dependency install (npm/pip) in sandbox
    │
    ▼
Testing Agent writes + runs tests in sandbox
    │
    ▼
Security Agent scans (secrets, injection, auth)
    │
    ▼
Snapshot → new version (only if tests pass)
```

### 10.2 Supported Stacks (Phase 1)

| Stack | Frontend | Backend | DB | Tests |
|-------|----------|---------|-----|-------|
| `web-fullstack` | React 18 + Vite + Tailwind | FastAPI + Python | SQLite → Postgres | pytest + Playwright |
| `web-frontend` | React 18 + Vite + Tailwind | — (static) | — | Playwright |

Phase 2 adds: `web-nextjs`, `mobile-capacitor` (wrapping web-frontend).

### 10.3 Project Template System

- Each stack has a **template**: known-good starter files (package.json,
  vite.config, main.py, etc.) with provenance `origin='platform'`.
- Agents generate *feature* files on top of the template — they don't
  reinvent the build system each time.
- Templates are versioned and tested in CI (the platform dogfoods: a
  nightly job builds a sample app from each template and runs its tests).

### 10.4 Export Format (Source ZIP)

```
my-app-source-v1.2.0.zip
├── README.md                  # generated by docs agent
├── package.json / requirements.txt / pyproject.toml
├── src/                       # all generated source
├── tests/                     # all generated tests
├── .env.example               # NO secrets; documents required vars
├── render.yaml                # deploy config (if deployed via platform)
├── Dockerfile                 # reproducible build
├── PROVENANCE.md              # human-readable provenance ledger
├── VERIFICATION.md            # verification record per requirement
└── manifest.json              # {version, files[], sha256[], generated_at}
```

**Guarantee:** unzipping and following the README produces a running app.
This is tested in CI for every template.

### 10.5 What's NOT in the Export

- Secrets (`.env` never exported; `.env.example` only).
- Platform-internal IDs (replaced with generic references).
- Other users' data. Ever.

---

## 11. Provenance Ledger

Every significant project event writes a `provenance_entries` row:

| Origin | Examples |
|--------|----------|
| `human` | User wrote the idea; user approved REQ-003; user uploaded a logo |
| `ai` | Frontend Agent generated `src/components/LoginForm.tsx` (execution_id) |
| `third_party` | `react@18.3.1` (npm); Tailwind; a starter template file |
| `platform` | Default `render.yaml`; build scripts; the export manifest itself |

The export's `PROVENANCE.md` renders this as a readable document:

```markdown
# Provenance — My App v1.2.0

## Human contributions (Bonez)
- Project idea and description
- Approved requirements REQ-001…REQ-007
- Uploaded logo asset (logo.png)
- Human verification: REQ-004 (audio playback)

## AI contributions
- Lead Builder: decomposed 7 requirements into 14 build tasks
- Frontend Agent: generated 23 files (src/...)
- Testing Agent: generated 11 tests, all passing

## Third-party
- react@18.3.1, vite@6.0.0, tailwindcss@3.4.0 (MIT)
- FastAPI@0.115.0 (MIT)

## Platform
- render.yaml deployment config
- Dockerfile, .env.example scaffolding
```

**No legal claims** about copyright of AI-generated code. The ledger is
factual (who/what did what), not a legal instrument.

---

## 12. Security Considerations

### 12.1 Threat Model

| Threat | Mitigation |
|--------|------------|
| Generated code attacks the host | Docker sandbox per build; no host network; resource limits |
| Prompt injection via user idea text | Idea text is data, never a system instruction; agent prompts are fixed templates with the idea in a delimited block |
| Secret leakage into generated code | Security Agent scans every version; `write_file` blocks secret-like paths; export excludes `.env` |
| One user's build accessing another's files | Per-execution sandbox; per-project workspace isolation; no shared volumes |
| Stolen session → project tampering | Session cookies `HttpOnly`, `Secure`, `SameSite=Lax`; CSRF tokens on mutations |
| API key theft | BYOK keys Fernet-encrypted; never returned by API; only fingerprint shown |
| Malicious connector OAuth | Least-privilege scopes; user explicitly approves per connector; actions logged |
| Abuse (crypto mining in sandbox) | CPU/time limits; no outbound network except allowlisted registries; mining patterns flagged |

### 12.2 Auth & Sessions

- Passwords: bcrypt (cost 12). No password hints. Rate-limited login
  (5 attempts / 15 min / IP).
- Sessions: server-side store (Postgres), 7-day expiry, rotating on privilege change.
- Google OAuth: Phase 2 (email/password first).

### 12.3 Rate Limiting & Abuse

- Agent dispatches: free tier 10/day, Pro 100/day (configurable).
- Build sandbox: max 15 min per execution; max 2 concurrent per user.
- API: 100 req/min/IP (generous for a builder tool; tightened if abused).

### 12.4 Audit Logging

Every security-relevant event is logged immutably:
logins, password changes, key additions, connector authorizations,
permission changes, export downloads, admin actions. (Separate
`audit_log` table, append-only, no UPDATE/DELETE grants to the app role.)

---

## 13. Deployment Architecture (Render + Neon)

```
                    ┌─────────────────────────┐
                    │   Cloudflare (DNS/CDN)   │
                    │   mommyididit.com        │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
   ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
   │  Static Site     │ │ Web Service  │ │  Background      │
   │  (React SPA)     │ │ (FastAPI)    │ │  Worker (arq)    │
   │  Free tier       │ │ Starter+     │ │  (Phase 2)       │
   └──────────────────┘ └──────┬───────┘ └──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
   ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
   │  Neon Postgres   │ │ Object Store │ │ Docker Host      │
   │  (primary DB)    │ │ (versions,   │ │ (build sandboxes)│
   │  + branches for  │ │  exports)    │ │ Phase 2:         │
   │  version snaps   │ │ R2 (Phase 2) │ │ separate service │
   └──────────────────┘ └──────────────┘ └──────────────────┘
```

### 13.1 Environment Variables (Render)

```
DATABASE_URL              # Neon connection string (REQUIRED — no silent SQLite fallback in prod)
SECRET_KEY                # session signing
FERNET_KEY                # credential encryption
OPENAI_API_KEY            # platform key (optional if all users BYOK)
ANTHROPIC_API_KEY         # platform key (optional)
STRIPE_SECRET_KEY         # platform billing (Phase 2)
RENDER_API_KEY            # deploy connector
GITHUB_OAUTH_*            # connector OAuth
STORAGE_PATH              # local disk path (Phase 1) / R2 credentials (Phase 2)
```

### 13.2 The DATABASE_URL Rule (Learned the Hard Way)

> **Production MUST fail fast if `DATABASE_URL` is unset.** No silent
> SQLite fallback. The app raises on boot with a clear error. SQLite is
> allowed only when `ENV=development` is explicitly set.

This rule exists because silent SQLite fallback on Render's ephemeral
disk caused data loss across the Bonez Labz apps.

### 13.3 Sandbox Execution in Production

Phase 1: sandbox runs as Docker-in-Docker on a dedicated Render service
(`mommy-sandbox`). The API server sends build jobs over an internal
authenticated HTTP API. Resource limits enforced by Docker.

Phase 2 (if scale demands): move to a dedicated VM (Hetzner) running
the sandbox pool, keeping Render for API + frontend.

---

## 14. Phased Build Plan

### Phase 0 — Foundation (Week 1–2)

- [ ] Repo + Render services (API + static frontend skeleton)
- [ ] Neon schema: users, projects, requirements, agent_types (seeded)
- [ ] Auth: signup/login/sessions
- [ ] Project CRUD + requirement CRUD
- [ ] AI requirement generation (via Provider Layer, OpenAI)
- [ ] `DATABASE_URL` fail-fast rule + loud dev-mode banner

**Exit criteria:** User can sign up, create a project, and get AI-generated
requirements. Deployed and live.

### Phase 1 — Real Builds (Week 3–6)

- [ ] Model Provider Layer (OpenAI + Anthropic, capability routing)
- [ ] Sandbox executor (Docker, `web-frontend` stack first)
- [ ] Agent orchestrator + `lead_builder`, `frontend`, `tester` agents
- [ ] Tool implementations: `write_file`, `read_file`, `run_tests`, `run_shell`
- [ ] Version snapshots on every file-changing execution
- [ ] Basic evidence + AI verification (with trivial-evidence filter)
- [ ] Project template system (`web-frontend`, then `web-fullstack`)
- [ ] Source ZIP export (must produce runnable app — CI-tested)

**Exit criteria:** A user can go IDEA → verified static website with
downloadable source that actually runs. The "holy shit, I built this" moment.

### Phase 2 — Trust & Safety (Week 7–9)

- [ ] Human verification flow (PASS/FAIL/BLOCKED with evidence)
- [ ] Verification conflicts (no-override enforcement)
- [ ] Stale-evidence invalidation on new versions
- [ ] Release gate with all 7 checks
- [ ] Regression detection + known-good tracking + rollback
- [ ] Security Agent (secret scanning)
- [ ] `backend`, `database`, `debugger`, `docs` agents (marked real)
- [ ] Release package ZIP + certificate PDF
- [ ] Provenance ledger + `PROVENANCE.md` in exports

**Exit criteria:** Full lifecycle IDEA → OWN works with honest gates.
A regression is caught automatically at least once in testing.

### Phase 3 — Connect & Publish (Week 10–12)

- [ ] Connector framework + GitHub connector (push source to user's repo)
- [ ] Render connector (one-click deploy)
- [ ] Deployment records + health checks
- [ ] BYOK UI (add/manage provider keys)
- [ ] Build credits ledger + metering
- [ ] `release`, `deployer` agents

**Exit criteria:** User can publish a built app to a live URL from the
platform and push source to their own GitHub.

### Phase 4 — Polish & Scale (Week 13+)

- [ ] `architect`, `qa` agents (flip from SIMULATED to real)
- [ ] Background worker (`arq` + Redis) for concurrent builds
- [ ] Object storage migration (local disk → R2)
- [ ] Google OAuth
- [ ] Team workspaces (Phase 2 of the business)
- [ ] Public API (`/api/v1` with API keys)
- [ ] Stripe billing for platform tiers

---

## 15. Open Questions & Risks

| # | Question / Risk | Impact | Mitigation / Next Step |
|---|-----------------|--------|------------------------|
| 1 | **Sandbox cost.** Docker builds per user could get expensive. | High | Start with strict limits (15 min, 2 concurrent); measure real costs in Phase 1 before promising free-tier builds |
| 2 | **LLM code quality.** Generated apps may have bugs the agents don't catch. | High | Testing Agent + regression detection are the safety net; human verification is the backstop; never claim "bug-free" |
| 3 | **Prompt injection** from malicious idea text. | Medium | Delimited idea blocks; fixed system prompts; sandbox isolation as defense in depth |
| 4 | **Render free-tier limits** for the API server. | Medium | Start on Starter ($7/mo); the platform itself is a revenue project |
| 5 | **Neon branching cost** at scale. | Low | Branches only for versions (not every execution); prune old non-known-good branches |
| 6 | **Legal: who owns AI-generated code?** | Medium | Provenance ledger is factual, not legal advice; Terms of Service assign output rights to the user; recommend user consult counsel for commercial use |
| 7 | **Competing with Base44/Replit.** | Medium | Differentiator is honesty + ownership + verification, not speed. The Base44 prototype proved the verification UX is the moat. |
| 8 | **Credit economics.** Real token costs unknown until measured. | High | Phase 0 instruments every LLM call; pricing set from data, not guesses; BYOK reduces platform exposure |

---

## Appendix A: Glossary

| Term | Meaning |
|------|---------|
| **Version** | Immutable snapshot of project source + manifest |
| **Known-good** | Latest version that passed regression against its baseline |
| **Evidence** | Test output, screenshot, log, or observation tied to a requirement + version |
| **Verification** | A verdict (pass/fail/blocked) on a requirement, issued by AI or human |
| **Conflict** | AI and human verifications disagree; resolved only by new evidence |
| **Release gate** | Automated evaluation of 7 checks; all must pass for release |
| **Provenance** | Factual record of who/what contributed each part (human/AI/third-party/platform) |
| **SIMULATED** | Labeled as not-yet-real; the UI must never present it as functional |

## Appendix B: What the Base44 Prototype Got Right (Preserve These Ideas)

1. The **verification workflow UX** — requirements board, evidence linking,
   human PASS/FAIL/BLOCKED flow. This is the moat; rebuild it faithfully.
2. The **honesty about simulated agents** — the prototype labeled 14/16
   agents as simulated. Keep that standard.
3. The **release gate that actually blocks** — the self-test proved it.
   Rebuild with the same integrity.
4. The **dual-authority principle** — no overrides either way. This is
   non-negotiable and carries over unchanged.
5. The **"holy shit, I actually built this"** feeling — the north star
   for UX. Every screen should reinforce: this is real, you made this.

---

*End of Architecture v1.0 — Ready for Phase 0 kickoff.*
