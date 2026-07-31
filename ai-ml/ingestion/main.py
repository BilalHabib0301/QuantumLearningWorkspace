"""
8. API Design
--------------
Free stack: FastAPI + Uvicorn — pip install fastapi uvicorn python-multipart
Run locally (from inside the ai-ml/ folder):
    uvicorn ingestion.main:app --reload
Endpoints:
  POST /ingest/pdf       (multipart file upload + user_id form field)
  POST /ingest/youtube   ({"url": "...", "user_id": "..."})
  POST /ingest/article   ({"url": "...", "user_id": "..."})
"""
import shutil
import tempfile
import os
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from ingestion.pdf.extractor import ingest_pdf
from ingestion.youtube.transcript import ingest_youtube
from ingestion.web.scraper import ingest_article
from embedding.chunker import chunk_document
from embedding.chroma_store import store_chunks

app = FastAPI(title="StudyMind AI - Content Ingestion Pipeline")


class URLRequest(BaseModel):
    url: str
    user_id: str


def _chunk_and_store(result: dict, user_id: str) -> dict:
    """Shared helper: chunk an ingested document and store it in ChromaDB."""
    document_id = str(uuid.uuid4())
    chunks = chunk_document(result)
    stored_count = store_chunks(
        chunks=chunks,
        user_id=user_id,
        document_id=document_id,
        title=result.get("title", ""),
    )
    return {
        "document_id": document_id,
        "title": result.get("title", ""),
        "chunks_stored": stored_count,
    }


# -----------------------------
# PDF INGESTION
# -----------------------------
@app.post("/ingest/pdf")
async def ingest_pdf_endpoint(
    file: UploadFile = File(...),
    user_id: str = Form(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = ingest_pdf(file_path=tmp_path, original_filename=file.filename)
        storage_info = _chunk_and_store(result, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {**result, **storage_info}


# -----------------------------
# YOUTUBE INGESTION
# -----------------------------
@app.post("/ingest/youtube")
async def ingest_youtube_endpoint(payload: URLRequest):
    try:
        result = ingest_youtube(payload.url)
        storage_info = _chunk_and_store(result, payload.user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {**result, **storage_info}


# -----------------------------
# ARTICLE INGESTION
# -----------------------------
@app.post("/ingest/article")
async def ingest_article_endpoint(payload: URLRequest):
    try:
        result = ingest_article(payload.url)
        storage_info = _chunk_and_store(result, payload.user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {**result, **storage_info}


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "StudyMind AI Content Ingestion Pipeline",
    }