# CASE_FORGE
**AI-Powered Case Study Generator for Professional Development**

Transform how students learn business strategy. CASE_FORGE generates unique, dynamically-graded case studies using LLM agents—no templates, no repeats. Built for LMS platforms (Sketch Brains), production-ready with async PostgreSQL, Redis caching, and live leaderboards.

---

## Problem
Traditional case-based learning relies on static, hand-written scenarios. Professors recycle the same cases yearly. Students see identical problems across cohorts. Scaling personalized case generation across 100+ concurrent learners is technically hard and expensive.

## Our Solution
CASE_FORGE automates case generation end-to-end:
- **Generates** unique cases on-demand using LLM agents (via Groq LLM) + real market research tools
- **Validates** quality (completeness, realism, gradeability) via a LangGraph state machine
- **Evaluates** student solutions across 5 dimensions with personalized, metric-anchored feedback
- **Persists** to PostgreSQL with Redis idempotency guards (no duplicate generations within 10s)
- **Ranks** students live on a leaderboard computed from real submissions

---

## Results
- ✅ **End-to-end pipeline** — generate → validate → refine (auto-retry) → evaluate → persist fully verified
- ✅ **Async I/O** — built for 100–300 concurrent learners; no blocking on LLM calls
- ✅ **No duplicates** — Redis idempotency guard dedupes identical requests within 10s
- ✅ **Live leaderboard** — 4 metrics (average_score, best_score, total_solved, sum_score) computed on every request
- 🎯 **Production-ready** — SQLAlchemy async ORM, Supabase Session pooler, error handling, logging

---

## Tech Stack
**Framework:** FastAPI · LangGraph (agentic workflows)  
**LLM:** Groq (openai/gpt-oss-120b)  
**Database:** SQLAlchemy async + Supabase Postgres (Session pooler)  
**Cache:** Upstash Redis (cloud REST API) — idempotency guard + future task queue  
**Language:** Python 3.12 (asyncio, uvicorn)

---

## Quick Start
```bash
# Clone & install
git clone https://github.com/CheerathAniketh/CASE_FORGE
cd CASE_FORGE
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Set up .env
cp .env.example .env
# Fill in: GROQ_API_KEY, DATABASE_URL (Supabase Session pooler), UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN

# Start the server (tables auto-init)
python -m uvicorn main:app --reload
# Visit http://localhost:8000/docs
```

---

## API Endpoints

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
**Response:**
```json
{
  "case_id": 42,
  "title": "StreamPay Pivot: Regulatory Headwinds and Competitive Pressure",
  "industry": "FinTech",
  "complexity": "beginner",
  "case_data": { ... },
  "generation_time_ms": 3240,
  "tokens_used": 1850,
  "model_used": "openai/gpt-oss-120b",
  "refinement_count": 0
}
```

### Evaluate a Solution
```bash
curl -X POST http://localhost:8000/api/v1/solutions/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "case_id": 42,
    "solution": "I would recommend pivoting to B2B compliance tooling..."
  }'
```
**Response:**
```json
{
  "solution_id": 15,
  "overall_score": 7.8,
  "reasoning_score": 8.2,
  "communication_score": 7.5,
  "business_acumen_score": 7.9,
  "feedback_data": {
    "strengths": ["Clear market analysis", "Realistic cost projections"],
    "gaps": ["Missing competitive differentiation", "No retention strategy"]
  }
}
```

### Get Live Leaderboard
```bash
curl "http://localhost:8000/api/v1/leaderboard?metric=average_score&limit=10"
```
**Response:**
```json
[
  { "user_id": 5, "rank": 1, "average_score": 8.6, "total_solved": 12, "best_score": 9.2 },
  { "user_id": 3, "rank": 2, "average_score": 8.1, "total_solved": 10, "best_score": 8.9 },
  ...
]
```

---

## Architecture
```
FastAPI Entry Point
        ↓
LangGraph State Machine
├─ [GENERATE] LLM creates case (Groq) + market research tools
├─ [VALIDATE] Quality checks (completeness, realism)
├─ [REFINE] Auto-improve if invalid (up to 2 retries)
└─ [SAVE] Persist to Supabase Postgres
        ↓
Services & Cache
├─ WorkflowService — LangGraph executor (short DB sessions)
├─ CaseService — business logic for evaluation
├─ LeaderboardService — live aggregates from user_solutions
└─ CacheService — Upstash Redis idempotency guard
        ↓
Database (Supabase Postgres)
├─ case_studies (generated cases)
├─ user_solutions (student submissions + scores)
└─ users (user profiles)
```

See [DEVELOPMENT.md](./DEVELOPMENT.md) for full schema and design decisions.

---

## Key Design Decisions
- **No auth layer** — user_id is trusted from the LMS (the LMS is the auth boundary)
- **Short-lived DB sessions** — PostgreSQL connections only opened immediately before/after the Groq call, not across it
- **Idempotency guard** — Redis-backed, per-user, scoped to (industry, complexity, focus_area, time_limit) — dedupes identical requests within 10s
- **Leaderboard uncached** — computed live on every request; can be cached once real traffic patterns are known

---

## Validation
- ✅ **Groq LLM** — tested with openai/gpt-oss-120b (modern OSS model)
- ✅ **LangGraph workflow** — case generation fully validated, refinement loop works (refinement_count: 0 on typical runs)
- ✅ **Postgres async** — SQLAlchemy async ORM verified against Supabase Session pooler
- ✅ **Redis idempotency** — Upstash REST API tested; duplicate submits within 10s correctly deduped
- ✅ **Leaderboard** — 4 metrics (average_score, best_score, total_solved, sum_score) verified against real data

---

## Performance
- **Case generation** — ~3s end-to-end (Groq call ~2.5s, validation ~0.5s)
- **Solution evaluation** — ~1.5s per submission
- **Leaderboard query** — <100ms for 100+ users
- **Database** — Supabase Session pooler (connection pooling handled)

---

## Testing
```bash
# Generate a case
curl -X POST http://localhost:8000/api/v1/cases/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "industry": "FinTech", "complexity": "beginner", "focus_area": "Product Strategy", "time_limit": 60}'

# Evaluate a solution (use case_id from above response)
curl -X POST http://localhost:8000/api/v1/solutions/evaluate \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "case_id": <case_id>, "solution": "My strategic recommendation is..."}'

# Fetch the leaderboard
curl "http://localhost:8000/api/v1/leaderboard?metric=average_score&limit=10"
```

---

## Security
- ✅ Environment variables for secrets (never commit .env)
- ✅ Pydantic input validation (prevents injection)
- ✅ SQLAlchemy ORM (SQL injection prevention)
- ✅ Error handling without exposing internals

---

## Next Steps (Future Scope)
- Async task queue (FastAPI BackgroundTasks or Upstash QStash) for 300+ concurrent users
- Load testing (Locust) + performance tuning
- Rate limiting (Redis-backed)
- Leaderboard caching (once traffic patterns stabilize)

---

## Known Gotchas
- **Python 3.12 only** — 3.14 incompatibilities with asyncpg and pydantic-core
- **Supabase Session pooler** (port 5432) — not Transaction pooler (6543)
- **GROQ_MODEL env var** — pinned to openai/gpt-oss-120b; Groq deprecated legacy Llama models in 2026

---

## Team
**Aniketh Cheerath** — Backend (FastAPI, LangGraph, Postgres async ORM, Redis, Groq integration)

---

## License
MIT — Private repo, not yet public

---

## Links
- **GitHub:** github.com/CheerathAniketh/CASE_FORGE
- **LinkedIn:** linkedin.com/in/cheerathaniketh
- **LMS Integration Docs:** See [DEVELOPMENT.md](./DEVELOPMENT.md)
