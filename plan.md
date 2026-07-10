# Codebase Audit & Fix Plan

A full review of the backend (FastAPI + SQLite + Groq) and frontend (vanilla JS) surfaced
correctness bugs, security issues, and edge cases. Fixes are grouped into **3 commits**
(no co-authors). Each section below maps to one commit.

Verified facts used throughout:
- `main.py` imports only `ai_service` and `phase2_ai`. The files `phase3_endpoints.py`,
  `dashboard_endpoint.py`, `alerts_endpoint.py`, `leads_endpoint.py`, `database.py`,
  `models.py`, `schemas.py` are **never imported** — dead code that duplicates live routes.
- Live JS: `app.js`, `generators.js`, `deal_tools.js`, `market_intelligence.js`,
  `prediction_page.js`, `copilot_page.js`. Dead JS (referenced by no HTML):
  `dashboard.js`, `phase3_copilot.js`, `phase3_dashboard.js`, `alerts_loader.js`.

---

## Commit 1 — Backend reliability, AI robustness & security (`backend/`)

**Reliability**
- **DB connection leaks** (`main.py`, ~15 handlers): `conn = get_db()` … `conn.close()`
  with no `try/finally`. Any exception between them leaks the SQLite handle and eventually
  causes "database is locked". → Wrap DB usage in `try/finally: conn.close()` (or a
  contextmanager helper) for every handler that currently closes bare.
- **`init_db()` at import time** (`main.py:260`): a bad path/locked DB fails the whole
  import. → Guard so failure degrades instead of crashing import.

**AI robustness**
- **`ai_service.py:320`**: `completion.choices[0].message.content.strip()` — `content` can be
  `None` and `choices` can be empty (`IndexError`/`AttributeError`). Crashes `/chat/test`.
  → `raw = (completion.choices[0].message.content or "").strip()` with an empty-`choices` guard.
- **Global RNG race** (`main.py:471`): `random.seed(seed)` mutates process-global RNG; sync
  handlers run in a threadpool so concurrent `/market/analyze` calls interfere. → Use a local
  `random.Random(seed)` instance.
- **Cache schema drift** (`main.py:364-375`): `ai_or_fallback` returns cached dict directly;
  a changed fallback schema → later `ai_data["key"]` `KeyError`. → Return `{**fallback, **cached}`.

**Security & config**
- **CORS** (`main.py:43-49`): `allow_origins=["*"]` + `allow_credentials=True` is invalid/
  insecure. → Explicit origins (localhost dev hosts) or `allow_credentials=False`.
- **API-key leak** (`main.py:~1476`): `/chat/test` returns `api_key[:8]+"..."` unauthenticated.
  → Stop returning key material.
- **Case-sensitive lookups** (`main.py:840-841`): region/horizon lookups don't lowercase like
  industry does → silent wrong defaults. → Normalize keys consistently.
- **Input validation** (`schemas`/`ScoreRequest`): negative budgets and empty strings accepted.
  → Add basic bounds (`ge=0`, `min_length`).

---

## Commit 2 — Frontend crash fixes & XSS hardening (live JS)

**Missing error handling / crashes**
- **`generators.js` `generateContent` (122-142) & `generateEmail` (144-162)**: no try/catch and
  no `res.ok` check — network failure = silent death; error body renders `undefined`.
  → Add try/catch + `res.ok` check mirroring `generatePitch`.
- **`generators.js` `analyzeMarket`**: catch only `console.error`, no UI feedback. → Surface error.
- **`generators.js` duplicate `getDealStrategy`/`getFollowupPlan`**: collide with `deal_tools.js`
  on `leads.html` (load-order fragile). → Remove the dead duplicates from `generators.js`.
- **`deal_tools.js` `getFollowupPlan` (117)**: `Object.entries(data.plan)` throws when `plan`
  missing. → Guard `if (!data.plan) { … return; }` and check `res.ok`.
- **`prediction_page.js` (41)**: unguarded `data.metrics_used.total_leads` + no `res.ok`.
  → Check `res.ok`, default `metrics_used` to `{}`.
- **`copilot_page.js` (83)**: mojibake `�` separator → replace with `•`.

**XSS hardening** (server/lead-supplied data rendered via `innerHTML`)
- **`app.js`**: `addMessage` (459), `formatToolResult` (427), `updateSuggestions` (452).
- **`copilot_page.js`**: `loadInsights`, `loadNextActions`, `loadSalesTrends`, `loadAlerts`.
- → Add an `escapeHtml()` helper and escape untrusted text before interpolation
  (use `textContent` for the user's own typed message).

---

## Commit 3 — Remove dead & duplicate code

All version-controlled, so removal is reversible. These are never imported/referenced and
several contain their own bugs (e.g. `alerts_endpoint.py` broken `COUNT(*)…LIMIT`,
`dashboard_endpoint.py` div-by-zero, `phase3_dashboard.js` wrong API field access):
- Backend: `phase3_endpoints.py`, `dashboard_endpoint.py`, `alerts_endpoint.py`,
  `leads_endpoint.py`, and the unused SQLAlchemy layer `database.py`, `models.py`, `schemas.py`
  (only if truly unreferenced — verify no import remains after Commit 1).
- Frontend: `dashboard.js`, `phase3_copilot.js`, `phase3_dashboard.js`, `alerts_loader.js`.

---

### Sequencing
1. Commit 1 (backend) → commit + push.
2. Commit 2 (frontend) → commit + push.
3. Commit 3 (cleanup) → commit + push.
