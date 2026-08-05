from __future__ import annotations
import time
from collections import defaultdict, deque
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional, List, Dict

router = APIRouter()


# ---------------- Request Models ---------------- #

class HistoryMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    history: Optional[List[HistoryMessage]] = None
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
    sources: List[Source]
    source_ids: List[str]
    rewritten_question: str
    grounded: bool
    retrieval_rounds: int
    hop_queries: List[str]
    conflict_hint: Optional[str] = None
    cached: bool
    timing: Timing


# ---- Simple in-memory rate limiter (10 requests / 60s per user/IP) ----
request_log: Dict[str, deque] = defaultdict(deque)
RATE_LIMIT = 10
WINDOW_SECONDS = 60


@router.post("/ask", response_model=AskResponse)
def mock_ask(request: AskRequest, req: Request, res: Response):
    # Identify the caller: X-User-Id header, or fall back to their IP
    user_key = req.headers.get("X-User-Id") or req.client.host
    now = time.time()

    # Clean out old requests outside the time window
    timestamps = request_log[user_key]
    while timestamps and timestamps[0] < now - WINDOW_SECONDS:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT:
        retry_after = int(WINDOW_SECONDS - (now - timestamps[0]))
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )