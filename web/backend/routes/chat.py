import time
from collections import defaultdict, deque
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# ---- Request / Response shapes (matches Team Mu's real /ask contract) ----

class HistoryMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    history: Optional[list[HistoryMessage]] = None
    top_k: Optional[int] = 4
    include_sources: Optional[bool] = True
    rerank: Optional[bool] = True
    multi_hop: Optional[bool] = True
    skip_cache: Optional[bool] = False


class Source(BaseModel):
    document: str
    chunk: str


class Timing(BaseModel):
    retrieval_ms: int
    llm_ms: int
    grounding_ms: int
    total_ms: int


class AskResponse(BaseModel):
    answer: str
    refused: bool
    sources: list[Source]
    source_ids: list[str]
    rewritten_question: str
    grounded: bool
    retrieval_rounds: int
    hop_queries: list[str]
    conflict_hint: Optional[str] = None
    cached: bool
    timing: Timing


# ---- Simple in-memory rate limiter (10 requests / 60s per user/IP) ----
request_log: dict[str, deque] = defaultdict(deque)
RATE_LIMIT = 10
WINDOW_SECONDS = 60


@router.post("/ask", response_model=AskResponse)
def mock_ask(request: AskRequest, req: Request, res: Response):
    # Identify the caller: X-User-Id header, or fall back to their IP
    client_ip = req.client.host if req.client else "unknown"
    user_key = req.headers.get("X-User-Id") or client_ip
    now = time.time()

    # Clean out old requests outside the time window
    timestamps = request_log[user_key]
    while timestamps and timestamps[0] < now - WINDOW_SECONDS:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT:
        retry_after = int(WINDOW_SECONDS - (now - timestamps[0]))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(max(retry_after, 1))},
        )

    timestamps.append(now)

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    # Clamp top_k between 1 and 8
    top_k = request.top_k or 4
    top_k = max(1, min(top_k, 8))

    # Fake timings for now — real backend will report actual numbers
    timing = {"retrieval_ms": 50, "llm_ms": 300, "grounding_ms": 20, "total_ms": 370}

    res.headers["X-Cache-Hit"] = "false"
    res.headers["X-Retrieval-Ms"] = str(timing["retrieval_ms"])
    res.headers["X-Llm-Ms"] = str(timing["llm_ms"])
    res.headers["X-Total-Ms"] = str(timing["total_ms"])

    sources = []
    source_ids = []
    if request.include_sources:
        sources = [{"document": "sample.pdf", "chunk": "chunk_1"}]
        source_ids = ["sample.pdf#chunk_1"]

    hop_queries = [request.question] if request.multi_hop else []

    return {
        "answer": f"This is a placeholder answer for: '{request.question}'",
        "refused": False,
        "sources": sources,
        "source_ids": source_ids,
        "rewritten_question": request.question,
        "grounded": True,
        "retrieval_rounds": 1,
        "hop_queries": hop_queries,
        "conflict_hint": None,
        "cached": False,
        "timing": timing,
    }