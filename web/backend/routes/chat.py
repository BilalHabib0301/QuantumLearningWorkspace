from __future__ import annotations
import httpx

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ---------------- Request Models ---------------- #

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


# ---------------- Proxy Endpoint ---------------- #

@router.post("/ask")
async def ask(request: AskRequest, req: Request):

    payload = {
        "question": request.question,
        "user_id": req.headers.get("X-User-Id", "guest"),
        "history": [
            {
                "role": h.role,
                "content": h.content,
            }
            for h in (request.history or [])
        ],
        "top_k": request.top_k,
        "include_sources": request.include_sources,
        "rerank": request.rerank,
        "multi_hop": request.multi_hop,
        "skip_cache": request.skip_cache,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "http://127.0.0.1:8001/ask",
                json=payload,
            )

        response.raise_for_status()

        return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )