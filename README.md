# CaseForge

**AI-Powered Case Study Generator for Professional Development**

Transform how students learn business strategy through dynamic, AI-generated case studies with intelligent evaluation and personalized feedback.

Built as part of the LMS platform at Sketch Brains.

---

## Status

**Backend: deployable.** Full generate → validate → evaluate → persist loop is verified end-to-end against a live Postgres database, with Redis-backed idempotency on generation and a live leaderboard. Not yet live — see [What's Left](#whats-left) below. Measured latency and validation results are in [Performance (measured)](#performance-measured).

---

## Overview

CaseForge is an intelligent case study generation platform built for educational institutions and corporate training. It uses **LangGraph state machines** and **LLMs** to create unique, realistic business scenarios on-demand — no templates, no repeats.

This backend is designed to be embedded into an existing LMS. It has **no built-in auth or frontend by design** — the LMS handles user identity and UI; this service just exposes a REST API.

---

## Features

### For Students
- Dynamic case generation — unique cases every time
- Multi-level difficulty: Beginner, Intermediate, Advanced
- AI-powered solution scoring across 5 dimensions
- Personalized, metric-anchored feedback
- Case history per user
- Industry variety: FinTech, Healthcare, E-commerce, SaaS, and more

### For Institutions
- API-first — built to sit behind an existing LMS, not stand alone
- No content management — cases generate automatically
- Real data tools baked into generation: market research, financial analysis, competitive intel
- Postgres-backed; concurrent multi-user load is a design goal and has not been load-tested
- Live leaderboard computed from submitted solutions
- Duplicate-submit protection via a short-TTL Redis idempotency guard

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Server                       │
├─────────────────────────────────────────────────────────┤
│
├─ REST API Routes
│  ├─ POST /api/v1/cases/generate
│  ├─ POST /api/v1/solutions/evaluate
│  ├─ GET /api/v1/cases/{case_id}
│  ├─ GET /api/v1/users/{user_id}/cases
│  ├─ GET /api/v1/leaderboard
│  └─ GET /api/v1/health
│
├─ LangGraph State Machine (Workflow)
│  ├─ Node: generate_case (Groq LLM)
│  ├─ Node: validate_case (Quality checks)
│  ├─ Node: refine_case (Auto-improve if invalid, up to 2 retries)
│  └─ Node: save_case (Database persistence)
│
├─ Services & Tools
│  ├─ GroqService (LLM API wrapper)
│  ├─ WorkflowService (LangGraph executor — DB session opened only around the
│  │    actual read/write, not across the Groq call)
│  ├─ CaseService (Business logic; evaluate_solution follows the same
│  │    short-lived-session pattern as WorkflowService)
│  ├─ LeaderboardService (live SQLAlchemy aggregates over user_solutions —
│  │    average_score / total_solved / best_score / sum_score, uncached)
│  ├─ CacheService (Upstash Redis — per-user idempotency guard on case
│  │    generation; does not cache case content)
│  └─ Tools (Market research, Financial analysis, Competitive intel)
│
└─ Database (SQLAlchemy async + Supabase Postgres)
   ├─ case_studies (Generated cases)
   ├─ user_solutions (Student submissions)
   └─ users (User profiles — currently unused; user_id is passed in from the LMS as a plain int)
```

**Note on auth:** there is no JWT/session layer in this service. `user_id` is trusted as-is from the request body. This is intentional for now since the LMS is the auth boundary — if that assumption ever changes, this needs a real auth layer before going further.

**Note on DB sessions:** `GET /cases/{id}` and `GET /users/{id}/cases` stay on request-scoped `Depends()` sessions — they have no slow external call in the middle, so the short-session pattern used elsewhere isn't needed there.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI 0.104 |
| **Agentic AI** | LangGraph 0.0.15 |
| **LLM** | Groq — `openai/gpt-oss-120b` (Groq deprecated the old Llama models in 2026; set via `GROQ_MODEL` env var) |
| **Database** | SQLAlchemy (async) + Supabase Postgres, via Session Pooler |
| **Cache** | Upstash Redis (cloud REST API) — idempotency guard on case generation, designed for a ~300-user LMS (not load-tested) |
| **Language** | Python 3.12 (do **not** use 3.14 — `asyncpg` and `pydantic-core` don't have compatible wheels yet) |
| **Async** | asyncio, uvicorn |

---

## Project Structure

```
caseforge/
├── main.py                          # FastAPI entry point
├── config.py                        # Settings from .env
├── graph.py                         # LangGraph state machine
├── requirements.txt                 # Dependencies
│
├── app/
│   ├── api/
│   │   └── routes.py               # REST endpoints
│   │
│   ├── services/
│   │   ├── groq.py                 # Groq API wrapper
│   │   ├── case.py                 # Case generation logic
│   │   ├── workflow.py             # LangGraph executor
│   │   ├── leaderboard.py          # Leaderboard aggregates
│   │   └── cache.py                # Upstash Redis idempotency guard
│   │
│   ├── workflows/
│   │   ├── state.py                # State definition
│   │   └── nodes.py                # Workflow nodes
│   │
│   ├── tools.py                    # Market research, financial analysis, etc.
│   ├── prompts.py                  # LLM prompts
│   ├── models.py                   # SQLAlchemy models
│   ├── db.py                       # Database setup
│   └── logger.py                   # Logging
│
└── scripts/
    ├── init_db.py                  # One-time DB initialization
    └── bench_generate.py           # Latency / validation benchmark
```

---

## Installation & Setup

### Prerequisites
- **Python 3.12** specifically (see Tech Stack note above)
- A Groq API key — free at [console.groq.com](https://console.groq.com)
- A Supabase project — free at [supabase.com](https://supabase.com)
- An Upstash Redis database — free at [upstash.com](https://upstash.com) (REST API, not a local Redis/Valkey install)

### 1. Clone & set up the venv
```bash
git clone https://github.com/CheerathAniketh/CASE_FORGE.git
cd CASE_FORGE
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
Create a `.env` file in the project root:
```
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-120b
DATABASE_URL=postgresql+asyncpg://postgres.<project-ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:5432/postgres
UPSTASH_REDIS_REST_URL=<your Upstash REST URL>
UPSTASH_REDIS_REST_TOKEN=<your Upstash REST token>
```

Get the `DATABASE_URL` from your Supabase project: **Connect → Direct (Connection string) tab → Session pooler**. If your DB password has special characters, URL-encode them (`@` → `%40`, etc.) or the connection string will fail to parse.

### 3. Run the server
```bash
python -m uvicorn main:app --reload
```
Server runs at `http://localhost:8000`. Tables are created automatically on startup via `init_db()` — no manual migration step needed for a fresh Supabase project.

API docs: `http://localhost:8000/docs`

---

## API Usage

### Generate a Case Study
```bash
curl -X POST http://localhost:8000/api/v1/cases/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "industry": "FinTech",
    "complexity": "beginner",
    "focus_area": "Product Strategy",
    "time_limit": 60
  }'
```
Repeated identical requests from the same user within a 10s window are deduped via a Redis idempotency guard (`case:{user_id}:{industry}:{complexity}:{focus_area}`) — this only blocks double-submits, it does not cache or reuse case content.

### Evaluate a Solution
```bash
curl -X POST http://localhost:8000/api/v1/solutions/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "case_id": 1,
    "solution": "Your proposed solution text here..."
  }'
```

### Get a Case
```bash
curl http://localhost:8000/api/v1/cases/1
```

### Get a User's Case History
```bash
curl http://localhost:8000/api/v1/users/1/cases
```

### Get the Leaderboard
```bash
curl "http://localhost:8000/api/v1/leaderboard?metric=average_score&limit=10"
```
`metric` accepts `average_score`, `total_solved`, `best_score`, or `sum_score`. Computed live from `user_solutions` on every request — not cached.

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

---

## LangGraph Workflow

```
START
  ↓
[GENERATE] - LLM creates raw case, using market/financial/competitive tools
  ↓
[VALIDATE] - Check quality & completeness
  ↓
  ├─ Valid?               → [SAVE] → END
  ├─ Invalid, retries left → [REFINE] → back to VALIDATE
  └─ Max retries hit       → [ERROR] → END
```

Measured: 44 of 44 generated cases passed validation on the first attempt (`refinements_used: 0`) across three benchmark runs, so the refine loop was never triggered. Small sample; see Performance (measured) below.

---

## Database Schema

### case_studies
```sql
CREATE TABLE case_studies (
  id INTEGER PRIMARY KEY,
  uuid VARCHAR(36) UNIQUE,
  user_id INTEGER,
  title VARCHAR(200),
  industry VARCHAR(100),
  complexity complexitylevel,   -- Postgres enum: beginner / intermediate / advanced
  focus_area VARCHAR(200),
  case_data JSON,
  generation_time_ms INTEGER,
  tokens_used INTEGER,
  model_used VARCHAR(100),
  refinement_count INTEGER,
  created_at DATETIME
);
```

### user_solutions
```sql
CREATE TABLE user_solutions (
  id INTEGER PRIMARY KEY,
  uuid VARCHAR(36) UNIQUE,
  user_id INTEGER,
  case_id INTEGER,
  solution_text VARCHAR(5000),
  overall_score FLOAT,
  reasoning_score FLOAT,
  communication_score FLOAT,
  business_acumen_score FLOAT,
  feedback_data JSON,
  created_at DATETIME
);
```

---

## Performance (measured)

Measured on 4 Oct 2026 with `scripts/bench_generate.py`: sequential `POST /api/v1/cases/generate` requests (beginner, Product Strategy, 60-minute limit, cycling through five industries) from a laptop in India to a local server, with Groq, Supabase Postgres and Upstash Redis in the cloud. These are small samples from one machine, so treat them as indicative, not as a benchmark of the service.

| Scenario | Requests | End-to-end p50 | End-to-end max | Reported generation p50 |
|---|---|---|---|---|
| Paced, one request every 10s | 12 | 4.63s | 13.38s | 3.06s |
| Back-to-back | 12 | 5.87s | 15.91s | 3.27s |
| Back-to-back | 20 | 11.90s | 14.18s | 10.20s |

- **What the reported time covers.** `generation_time_ms` is timed inside the LangGraph workflow (tools, Groq call, validation). It excludes the Postgres save (1.4 to 2.4s in our logs) and the Redis calls, which are part of the end-to-end figure.
- **The Groq call.** In the logged calls the model's own compute was about 2.0 to 3.0s for 970 to 1,260 completion tokens, and every call ended with `finish_reason=stop`, so none hit the 2,048-token cap.
- **Slowdown under back-to-back requests.** After roughly 7 to 8 requests in a row, end-to-end time rose from about 4 to 5s to 8 to 16s. In the logged slow calls the elapsed time (7 to 14s) was far above Groq's reported compute (about 2.6 to 3.0s), so the extra time was spent outside Groq's processing. It disappeared when requests were spaced 10s apart (the one slow paced request, 13.38s, was the first, sent right after the back-to-back run). This is consistent with rate limiting and client-side retries; we did not confirm the cause. The slowest paced request is why the table shows max, not p95, for such small samples.
- **Validation.** 44 of 44 generated cases passed validation on the first attempt, across one complexity level and focus area.
- **Idempotency guard.** A duplicate request inside the 10s window returned in 0.027s (the server logged a cache hit), against 5.55s for the original.
- **Not measured.** Solution-evaluation latency, leaderboard latency, parallel requests, and behaviour under real load. The 100 to 300 concurrent user figure elsewhere in this README is a design target, not a result.

---

## What's Left

This backend works end-to-end locally against production Postgres. Not yet done:

- [ ] **Deploy target** — not yet decided (Render / Railway / Fly / other). Blocks actual public deployment.
- [ ] **CORS lockdown** — `main.py` currently allows `allow_origins=["*"]`. Needs to be scoped to the LMS's actual domain before going live. Blocked on getting that domain.
- [x] **DB session lifetime** — done. `WorkflowService` and `CaseService.evaluate_solution` now open a Postgres session only immediately before/after the Groq call, not across it.
- [ ] **Async task queue (Redis)** — for handling 100–300 concurrent users without blocking on Groq in-request. Three approaches scoped (FastAPI `BackgroundTasks`, RQ/arq + worker on Upstash Redis, or Upstash QStash) — build is on hold pending a scope decision from the team lead, since the three options solve meaningfully different problems.
- [ ] **Load testing (Locust)** — depends on the async task queue being in place first.
- [ ] **Rate limiting** — none currently. Would likely ride on the same Redis instance as the task queue. Our benchmark saw latency rise under back-to-back requests (see [Performance (measured)](#performance-measured)).
- [ ] **Leaderboard caching** — leaderboard reads are uncached and computed live on every request; worth revisiting once real traffic patterns are known.
- [ ] **Confirm with team**: `CaseService.generate_case` looks like dead code — `routes.py` calls `WorkflowService.generate_case_with_workflow()` instead. Kept functional for now, pending confirmation before removal.

---

## Known Issues / Gotchas

- **Python 3.14 will not work.** `asyncpg` and `pydantic-core` (compiled dependencies) don't yet have 3.14 wheels — use 3.12.
- If you hit `ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'` on import, it means your Python patch version is 3.12.4+ and your `pydantic` is too old — this repo already pins `pydantic>=2.9.0` to avoid it, don't downgrade it.
- Supabase's **Session pooler** (port 5432) is what's configured here, not the Transaction pooler (6543) — the transaction pooler breaks asyncpg's default prepared-statement behavior with SQLAlchemy unless explicitly disabled.
- Cross-region latency is real: Supabase pooler region vs. server region adds a few seconds to DB round-trips. Worth picking a region close to wherever this actually deploys.
- Local dev uses **Upstash Redis** (cloud REST API) to match production, not a local Valkey/Redis install — if you have a system Redis running locally it's unused by the app and only useful for manual `redis-cli`-style debugging.
- **A dead Redis is slow, not fatal.** If the Upstash host cannot be reached, generation still works, but each cache call waits about 3 seconds before failing (we saw roughly 6 seconds added per request when our database had been deleted on the provider side). A shorter cache timeout would fix this and is not done yet.

---

## Security

- Environment variables for secrets (never commit `.env`)
- Input validation via Pydantic (types and shapes only). The student's solution text is sent to the LLM for scoring; we have not tested or mitigated prompt injection against the evaluator.
- SQL injection prevention via SQLAlchemy
- No auth layer — see Architecture note above; the LMS is the trust boundary
- Error handling without exposing internals

---

## Author

Built by Aniketh Cheerath — Sketch Brains

**Contact:** cheerathaniketh@gmail.com

---

## Recent Updates

- **Aug 18, 2026** — Added Redis (Upstash) idempotency guard on case generation, a live leaderboard endpoint, and fixed a stale `GROQ_MODEL` pointing at a deprecated Llama model.
- **Aug 18, 2026 (evening)** — Closed out the DB session lifetime issue: Postgres sessions in `WorkflowService` and `CaseService.evaluate_solution` no longer stay open across the multi-second Groq call. Also fixed a hardcoded model name in the saved DB record and scoped three options for the still-pending async task queue.
- **Oct 4, 2026** — Benchmarked case generation (see Performance), added `scripts/bench_generate.py` and a per-call Groq timing log line, and replaced a deleted Upstash Redis database.

For full historical detail beyond this summary, see the repo's commit history.

---

## Resources

- [LangGraph Docs](https://python.langchain.com/docs/langgraph)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Groq API Docs](https://console.groq.com/docs)
- [Supabase Docs](https://supabase.com/docs)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org)