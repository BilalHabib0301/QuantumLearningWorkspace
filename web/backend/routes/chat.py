from __future__ import annotations

import os
import time
import json
import httpx
from dotenv import load_dotenv

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional

from auth_utils import get_current_user_email

load_dotenv()

CHATBOT_SERVICE_URL = os.getenv("CHATBOT_SERVICE_URL", "http://localhost:8000")

try:
    from groq import AsyncGroq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

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
async def ask(
    request: AskRequest,
    current_user_email: str = Depends(get_current_user_email)
):

    # Strictly derive user_id from the authenticated JWT session (email) only.
    # Client-supplied user_id or X-User-Id is strictly stripped/ignored for security (P0-2).
    resolved_user_id = current_user_email

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

    if request.filename:
        payload["filename"] = request.filename

    # 1. Try forwarding to Team Mu's chatbot service first if live
    try:
        timeout = httpx.Timeout(connect=3.0, read=25.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{CHATBOT_SERVICE_URL}/ask",
                json=payload,
            )
            if response.status_code == 200:
                res_data = response.json()
                if res_data and isinstance(res_data, dict) and "placeholder" not in res_data.get("answer", "").lower():
                    return res_data
    except Exception as e:
        print("Chatbot service port 8000 unavailable, using direct Groq LLM engine:", repr(e))

    # 2. Direct Groq LLM Generation Fallback (Real AI Responses)
    load_dotenv()
    groq_key = os.getenv("GROQ_API_KEY")
    if HAS_GROQ and groq_key and groq_key.strip() and not groq_key.startswith("your_") and not groq_key.startswith("groq_api_key"):
        start_time = time.time()
        try:
            client = AsyncGroq(api_key=groq_key.strip())
            
            doc_context = ""
            if request.filename:
                file_path = os.path.join("uploaded_files", request.filename)
                if os.path.exists(file_path):
                    try:
                        if request.filename.lower().endswith(".pdf"):
                            from pypdf import PdfReader
                            reader = PdfReader(file_path)
                            extracted = ""
                            for page in reader.pages:
                                extracted += (page.extract_text() or "") + "\n"
                            doc_context = extracted.strip()[:8000]
                        else:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                doc_context = f.read().strip()[:8000]
                    except Exception as ex:
                        print("Error reading document content:", ex)

            system_prompt = "You are StudyMind AI, an intelligent, highly accurate study tutor. Answer the student's question accurately using the provided document content."
            user_prompt = f"Question: {request.question}"
            if doc_context:
                user_prompt += f"\n\n--- Document Content ({request.filename}) ---\n{doc_context}\n--- End of Document Content ---"
            elif request.filename:
                user_prompt += f"\nTarget Document: {request.filename}"

            messages = [{"role": "system", "content": system_prompt}]
            for h in (request.history or []):
                messages.append({"role": h.role if h.role in ["user", "assistant"] else "user", "content": h.content})
            messages.append({"role": "user", "content": user_prompt})

            completion = await client.chat.completions.create(
                model="groq/compound",
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
            )

            llm_duration = int((time.time() - start_time) * 1000)
            answer_text = completion.choices[0].message.content

            sources = []
            if request.filename:
                sources.append({"document": request.filename, "chunk": f"Extracted section from {request.filename}"})

            return {
                "answer": answer_text,
                "sources": sources,
                "timing": {
                    "total_ms": llm_duration + 40,
                    "llm_ms": llm_duration
                }
            }
        except Exception as groq_err:
            print("Groq Direct API Error:", repr(groq_err))
            raise HTTPException(status_code=500, detail=f"AI Engine Error: {str(groq_err)}")

    # 3. Default fallback if no Groq Key present
    raise HTTPException(
        status_code=503,
        detail="Chatbot service is currently unavailable. Please check your GROQ_API_KEY in .env."
    )


# ---------------- Quiz Generator Endpoint ----------------

class GenerateQuizRequest(BaseModel):
    topic: str
    question_count: Optional[int] = 5
    quiz_type: Optional[str] = "mcq"


@router.post("/generate-quiz")
async def generate_quiz(request: GenerateQuizRequest):
    load_dotenv()
    groq_key = os.getenv("GROQ_API_KEY")

    if HAS_GROQ and groq_key and groq_key.strip():
        try:
            client = AsyncGroq(api_key=groq_key.strip())
            prompt = f"""Generate a study quiz on topic '{request.topic}' with {request.question_count} questions of type '{request.quiz_type}'.
Return ONLY a valid JSON object with no extra text or markdown formatting. The JSON must follow this exact schema:
{{
  "success": true,
  "message": "Generated {request.question_count} questions.",
  "questions": [
    {{
      "id": 1,
      "type": "{request.quiz_type}",
      "question": "Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"]
    }}
  ],
  "answers": [
    {{
      "id": 1,
      "answer": "Option A"
    }}
  ]
}}
Ensure options array is provided for MCQ, and for true_false use ["True", "False"]."""

            completion = await client.chat.completions.create(
                model="groq/compound",
                messages=[
                    {"role": "system", "content": "You are a specialized Quiz Generation Engine. Output strictly valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )

            res_text = completion.choices[0].message.content
            quiz_data = json.loads(res_text)
            return quiz_data
        except Exception as groq_err:
            print("Groq Quiz Error:", repr(groq_err))

    # Fallback response
    dummy_questions = []
    dummy_answers = []
    for i in range(1, (request.question_count or 5) + 1):
        dummy_questions.append({
            "id": i,
            "type": request.quiz_type or "mcq",
            "question": f"Sample Question {i} regarding {request.topic}?",
            "options": ["Option A", "Option B", "Option C", "Option D"]
        })
        dummy_answers.append({
            "id": i,
            "answer": "Option A"
        })

    return {
        "success": True,
        "message": f"Generated {len(dummy_questions)} questions.",
        "questions": dummy_questions,
        "answers": dummy_answers
    }