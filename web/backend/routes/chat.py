from __future__ import annotations

import httpx

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ---------------- Request Models ----------------

class HistoryMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    filename: Optional[str] = None
    history: Optional[list[HistoryMessage]] = None
    top_k: Optional[int] = 4
    include_sources: Optional[bool] = True
    rerank: Optional[bool] = True
    multi_hop: Optional[bool] = True
    skip_cache: Optional[bool] = False


# ---------------- Proxy Endpoint ----------------

@router.post("/ask")
async def ask(request: AskRequest, req: Request):

    # Prefer user_id from request body.
    # If not available, use X-User-Id header.
    # Finally, fall back to guest.
    resolved_user_id = (
        request.user_id
        or req.headers.get("X-User-Id")
        or "guest"
    )

    # Build payload for chatbot service
    payload = {
        "question": request.question,
        "user_id": resolved_user_id,
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

    print("PROXY PAYLOAD:", payload)

    # Only send filename when it is actually provided
    if request.filename:
        payload["filename"] = request.filename

    try:
        # Chatbot can take 20-30+ seconds because of
        # retrieval + reranking + multi-hop + LLM generation.
        timeout = httpx.Timeout(
            connect=10.0,
            read=60.0,
            write=10.0,
            pool=10.0,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:

            response = await client.post(
                "http://127.0.0.1:8000/ask",
                json=payload,
            )

        # Successful chatbot response
        if response.status_code == 200:
            return response.json()

        # Chatbot returned an error
        print("CHATBOT STATUS:", response.status_code)
        print("CHATBOT RESPONSE:", response.text)

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    # Preserve HTTPException raised above
    except HTTPException:
        raise

    # Chatbot took longer than read timeout
    except httpx.ReadTimeout as e:
        print("CHATBOT CONNECTION ERROR: ReadTimeout")
        print("ERROR:", repr(e))

        raise HTTPException(
            status_code=504,
            detail="Chatbot took too long to respond.",
        )

    # Could not connect to chatbot service
    except httpx.ConnectError as e:
        print("CHATBOT CONNECTION ERROR: ConnectError")
        print("ERROR:", repr(e))

        raise HTTPException(
            status_code=503,
            detail=(
                "Chatbot service is unavailable. "
                "Please make sure the chatbot server is running on port 8000."
            ),
        )

    # Any other unexpected error
    except Exception as e:
        print("CHATBOT CONNECTION ERROR:", repr(e))

        raise HTTPException(
            status_code=503,
            detail=(
                "Chatbot service is currently unavailable. "
                "Please make sure it's running and try again."
            ),
        )