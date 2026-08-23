from __future__ import annotations

import os
import logging
from typing import Optional, List, Dict, Any
import httpx
from dotenv import load_dotenv

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth_utils import get_current_user_email

load_dotenv()

logger = logging.getLogger("uvicorn")
router = APIRouter()

CHATBOT_SERVICE_URL = os.getenv("CHATBOT_SERVICE_URL", "http://127.0.0.1:8000")


class HistoryItem(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    history: Optional[List[HistoryItem]] = None
    filename: Optional[str] = None
    top_k: Optional[int] = 5
    include_sources: Optional[bool] = True
    rerank: Optional[bool] = True
    multi_hop: Optional[bool] = False
    skip_cache: Optional[bool] = False


# ---------------- Proxy Endpoint ----------------

@router.post("/ask")
async def ask(
    request: AskRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    # Strictly derive user_id from the authenticated JWT session (email) only.
    resolved_user_id = current_user_email

    # Build payload for chatbot service
    payload: Dict[str, Any] = {
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

    if request.filename:
        payload["filename"] = request.filename

    target_url = f"{CHATBOT_SERVICE_URL.rstrip('/')}/ask"

    try:
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

        if response.status_code == 200:
            return response.json()

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

    except HTTPException:
        raise

    except httpx.ReadTimeout as e:
        logger.warning(f"Chatbot connection timeout: {e}")
        raise HTTPException(
            status_code=504,
            detail="Chatbot took too long to respond. Please try again.",
        )

    except httpx.ConnectError as e:
        logger.warning(f"Chatbot connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "Chatbot service is unavailable. "
                f"Please make sure the chatbot server is running on {CHATBOT_SERVICE_URL}."
            ),
        )

    except Exception as e:
        logger.error(f"Chatbot unexpected error: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "Chatbot service is currently unavailable. "
                "Please make sure it's running and try again."
            ),
        )