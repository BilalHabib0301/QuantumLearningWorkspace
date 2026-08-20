from __future__ import annotations

import os
import httpx
import logging

from fastapi import APIRouter, HTTPException, Request
from models import AskRequest, HistoryMessage

logger = logging.getLogger("uvicorn")
router = APIRouter()

CHATBOT_SERVICE_URL = os.getenv("CHATBOT_SERVICE_URL", "http://127.0.0.1:8000")


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

    # Only send filename when it is actually provided
    if request.filename:
        payload["filename"] = request.filename

    target_url = f"{CHATBOT_SERVICE_URL.rstrip('/')}/ask"

    try:
        # Chatbot can take 20-30+ seconds because of
        # retrieval + reranking + multi-hop + LLM generation.
        timeout = httpx.Timeout(
            connect=10.0,
            read=90.0,
            write=10.0,
            pool=10.0,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                target_url,
                json=payload,
            )

        # Successful chatbot response
        if response.status_code == 200:
            return response.json()

        # Chatbot returned an error status code
        error_detail = response.text
        try:
            err_json = response.json()
            if isinstance(err_json, dict) and "detail" in err_json:
                error_detail = err_json["detail"]
        except Exception:
            pass

        raise HTTPException(
            status_code=response.status_code,
            detail=error_detail,
        )

    # Preserve HTTPException raised above
    except HTTPException:
        raise

    # Chatbot took longer than read timeout
    except httpx.ReadTimeout as e:
        logger.warning(f"Chatbot connection timeout: {e}")
        raise HTTPException(
            status_code=504,
            detail="Chatbot took too long to respond. Please try again.",
        )

    # Could not connect to chatbot service
    except httpx.ConnectError as e:
        logger.warning(f"Chatbot connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "Chatbot service is unavailable. "
                f"Please make sure the chatbot server is running on {CHATBOT_SERVICE_URL}."
            ),
        )

    # Any other unexpected error
    except Exception as e:
        logger.error(f"Chatbot unexpected error: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "Chatbot service is currently unavailable. "
                "Please make sure it's running and try again."
            ),
        )