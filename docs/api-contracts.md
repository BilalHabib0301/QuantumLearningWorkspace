# API Contracts

Cross-team HTTP contracts for StudyMind. Team Mu owns the chatbot RAG service;
Team Pluto (Web) will call it from the frontend.

---

## Chatbot RAG API (Team Mu)

**Service root:** `chatbot/rag-engine/` (separate from `web/backend/`)

**Default local base URL:** `http://127.0.0.1:8000`

**Run:**

```bash
cd chatbot
pip install -r requirements.txt
cd rag-engine
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Env vars: see `chatbot/rag-engine/.env.example` (includes `ENABLE_CACHE`, `RATE_LIMIT_MAX`, `ENABLE_MULTI_HOP`, etc.).

**Pipeline:** query rewrite → multi-hop retrieve → optional re-rank → relevance gate → answer → grounding check. `/ask` also applies auth, cache, rate limits, and timing.

---

### `GET /health`

**Response `200`:**

```json
{
  "status": "ok",
  "ready": true,
  "chunks_indexed": 12,
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 4,
  "max_distance": 1.2,
  "cache_entries": 3,
  "cache_hits": 12,
  "cache_backend": "memory",
  "rate_limit_backend": "memory",
  "groq_configured": true
}
```

| Field | Description |
|-------|-------------|
| `ready` | `true` when the embedding index finished startup warmup |
| `status` | `ok` when ready; `warming` during startup |
| `cache_backend` | `memory` or `redis` |
| `rate_limit_backend` | `memory` or `redis` |
| `groq_configured` | Whether `GROQ_API_KEY` is set (answers still require a valid key) |

---

### `POST /ask`

#### Authentication

Requires header: `Authorization: Bearer <jwt>`

The token is verified against `JWT_SECRET_KEY` (HS256) — the same secret the Web team's `/login` issues tokens with. The user's identity (email) is read from the token's `sub` claim, **not** from the request body. There is no `user_id` field in the request anymore — that was a security fix (previously a client could claim to be any user just by sending a `user_id`).

| Failure | Status | Body |
|---------|--------|------|
| Missing `Authorization` header | `403` | `{"detail": "Not authenticated"}` (FastAPI's default — `auth.py` never runs) |
| Token present but invalid/expired | `401` | `{"detail": "Could not validate credentials."}` |
| Server missing `JWT_SECRET_KEY` | `500` | `{"detail": "Server is not configured with a JWT secret."}` |

#### Request body

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|--------|
| `question` | string | yes | — | Non-empty, max 2000 chars |
| `history` | array | no | omit | Triggers query rewrite |
| `top_k` | integer | no | `4` | Clamped **1–8** |
| `include_sources` | boolean | no | `true` | Rich `sources` objects |
| `rerank` | boolean | no | `true` | LLM re-rank |
| `multi_hop` | boolean | no | `true` | Agentic retrieval hops |
| `skip_cache` | boolean | no | `false` | Bypass cache; or header `X-Skip-Cache: 1` |

No `user_id` field — identity comes from the JWT.

**Rate limit:** 10 requests / 60s per authenticated user (keyed by the JWT `sub` email). Returns **429** with `Retry-After` header. Rate limiting requires a valid token — an unauthenticated request fails at the auth step (403/401) before rate limiting is ever checked.

**Example request:**

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{"question": "Where does the Calvin cycle take place?"}'
```

#### Response `200`

| Field | Type | Notes |
|-------|------|--------|
| `answer` | string | Final answer text |
| `refused` | boolean | `true` if question was off-topic / ungrounded |
| `no_documents` | boolean | `true` if the user has no uploaded documents at all |
| `top_k` | integer | Effective `top_k` used |
| `sources` | array \| null | Present when `include_sources: true` |
| `source_ids` | array | Chunk ids used |
| `rewritten_question` | string | Query after history-aware rewrite |
| `grounded` | boolean \| null | Faithfulness check result |
| `retrieval_rounds` | integer | Number of multi-hop rounds |
| `hop_queries` | array | Queries used per hop |
| `conflict_hint` | boolean | `true` if sources disagree |
| `cached` | boolean | `true` if served from in-memory cache |
| `timing` | object | `{retrieval_ms, llm_ms, grounding_ms, total_ms}` |

**Response headers:** `X-Cache-Hit`, `X-Retrieval-Ms`, `X-Llm-Ms`, `X-Total-Ms`

**Example response:**

```json
{
  "answer": "The Calvin cycle takes place in the stroma of the chloroplast.",
  "refused": false,
  "no_documents": false,
  "top_k": 4,
  "sources": [
    {"id": "pdf_chunk_3", "distance": 0.41, "preview": "...Calvin cycle occurs in the stroma...", "source": "biology_notes.pdf", "document": "biology_notes.pdf"}
  ],
  "source_ids": ["pdf_chunk_3"],
  "rewritten_question": "Where does the Calvin cycle take place?",
  "grounded": true,
  "retrieval_rounds": 1,
  "hop_queries": ["Where does the Calvin cycle take place?"],
  "conflict_hint": false,
  "cached": false,
  "timing": {"retrieval_ms": 410.2, "llm_ms": 1820.5, "grounding_ms": 310.1, "total_ms": 2540.8}
}
```

**Example 401 (missing/invalid token):**

```json
{"detail": "Could not validate credentials."}
```

**Cache rules:** Identical question + history + `top_k` / `rerank` / `multi_hop`, per authenticated user, hits cache. Refusals and `grounded: false` answers are **not** cached.

---

### `POST /ask/stream`

Streams the answer as **NDJSON** (`Content-Type: application/x-ndjson`). Same request body as `/ask`. Rate limited identically.

**Authentication:** Same as `/ask` — requires `Authorization: Bearer <jwt>`. See failure table above.

**Event types:**

1. **metadata** (first line) — retrieval complete; includes `source_ids`, `hop_queries`, partial `timing`, `refused`, `cached`.
2. **token** — `{"type":"token","content":"..."}` per text delta.
3. **done** — final `grounded`, full `timing`, `cached`.
4. **error** — `{"type":"error","detail":"..."}` on failure.

**Refusal:** metadata includes `refused: true` and `answer` with refusal text; no token events; then `done`.

**Test client:**

```bash
cd chatbot/rag-engine
python scripts/stream_client.py "Where does the Calvin cycle occur?"
```

**Example metadata event:**

```json
{"type":"metadata","refused":false,"source_ids":["pdf_chunk_1"],"rewritten_question":"...","retrieval_rounds":1,"hop_queries":["..."],"grounded":null,"cached":false,"timing":{"retrieval_ms":420,"llm_ms":null,"total_ms":null}}
```

**Example done event:**

```json
{"type":"done","grounded":true,"cached":false,"timing":{"retrieval_ms":420,"llm_ms":1800,"grounding_ms":350,"total_ms":2570}}
```

---

### Errors

| Status | When |
|--------|------|
| `400` | Empty / invalid `question` |
| `401` | Token present but invalid/expired |
| `403` | Missing `Authorization` header |
| `429` | Rate limit exceeded (`Retry-After` header) |
| `503` | Engine not ready, or missing `GROQ_API_KEY` |

---

## Web backend (Team Pluto)

See `web/backend/` — `GET /health`. Chatbot `/ask` lives only on the Mu service.

---

## Ingestion (Team Lambda)

See `ai-ml/ingestion/`. Extracted document text must be treated as **untrusted data** when fed into RAG (see `docs/architecture.md` — Team Mu RAG security).



---

## Quiz Generation (Team Lambda)

**Service root:** `ai-ml/quiz_generator/`

**Default local base URL:** `http://127.0.0.1:8002`

**Run:**

```bash
cd ai-ml
uvicorn quiz_generator.app.main:app --reload --port 8002
```

Interactive docs: [http://127.0.0.1:8002/docs](http://127.0.0.1:8002/docs)

Env vars (root `.env`): `GROQ_API_KEY`, `PINECONE_API_KEY`, `MONGODB_URI`, `MONGODB_DB`, `MONGODB_COLLECTION`.

**Pipeline:** topic → embedding search (Pinecone) → full text resolve (MongoDB) → LLM generates structured questions per `quiz_type` → split into a public `questions` list (no answers) and a server-side `answers` list, matched by `question_id`.

---

### `GET /health`

**Response `200`:**
```json
{"status": "ok"}
```

---

### `POST /generate-quiz`

#### Request body

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|--------|
| `topic` | string | yes | — | Non-empty |
| `question_count` | integer | no | `5` | Clamped **1–20** |
| `quiz_type` | string | yes | — | One of: `mcq`, `true_false`, `fill_blank`, `short_answer` |

#### Response `200`

```json
{
  "success": true,
  "message": "Generated 3 questions.",
  "questions": [
    {
      "question_id": "74724f0b-4d3c-4d7c-8752-e1ec089c262a",
      "question": "Where does photosynthesis primarily occur in plant cells?",
      "question_type": "mcq",
      "options": ["Roots", "Stems", "Leaves", "Flowers"],
      "difficulty": "medium",
      "topic": "photosynthesis"
    }
  ],
  "answers": [
    {
      "question_id": "74724f0b-4d3c-4d7c-8752-e1ec089c262a",
      "answer": "Leaves",
      "explanation": null
    }
  ]
}
```

**Note:** `questions` (shown to the user before submission) never includes the correct answer. Answers are returned in a separate list, matched by `question_id`, so the frontend can grade after submission without exposing answers upfront. `options` is `null` for `fill_blank` and `short_answer` types, and `["True", "False"]` for `true_false`.

#### Errors

| Status | When |
|--------|------|
| `400` | Invalid `quiz_type`, or no relevant content found for `topic` (returned as `success: false` in body) |
| `502` | Upstream generation error (e.g. LLM returned malformed data) |