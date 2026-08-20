import os
import shutil
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from bson import ObjectId

from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

from models import (
    SignupRequest,
    LoginRequest,
    Upload,
    ChatMessage,
    ChangePasswordRequest,
    QuizResult,
    QuizResultRequest,
)
from database import (
    get_users_collection,
    get_uploads_collection,
    get_chat_history_collection,
    get_quiz_results_collection,
)
from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user_email,
    verify_internal_service_key,
)
from routes.chat import router as chat_router
from routes.oauth import router as oauth_router
from routes.quiz import router as quiz_router
import httpx

logger = logging.getLogger("uvicorn")

app = FastAPI(title="StudyMind AI Backend")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(oauth_router)
app.include_router(quiz_router)


UPLOAD_DIRECTORY = "uploaded_files"
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:8001")

async def process_file_ingestion(file_id, filename: str, user_id: str):
    """Forward the uploaded file to the ingestion service for chunking + embedding."""
    uploads = get_uploads_collection()
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    new_status = "Ready"
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(
                        f"{INGESTION_SERVICE_URL.rstrip('/')}/ingest/pdf",
                        files={"file": (filename, f, "application/pdf")},
                        data={"user_id": user_id},
                    )
            if response.status_code != 200:
                logger.warning(f"Ingestion service responded with {response.status_code}")
                new_status = "Failed"
        except Exception as e:
            logger.warning(f"Ingestion error for {filename}: {e}")
            new_status = "Failed"
    else:
        new_status = "Failed"

    query: Dict[str, Any] = {"user_id": user_id}
    if file_id:
        try:
            query["_id"] = ObjectId(str(file_id))
        except Exception:
            query["_id"] = str(file_id)
    else:
        query["filename"] = filename

    await uploads.update_one(query, {"$set": {"status": new_status}})


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/signup")
async def signup(request: SignupRequest):
    users = get_users_collection()
    email_clean = request.email.strip().lower()

    existing_user = await users.find_one({"email": email_clean})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed = hash_password(request.password)

    new_user = {
        "email": email_clean,
        "hashed_password": hashed,
        "created_at": datetime.now(timezone.utc).strftime("%B %d, %Y"),
    }

    await users.insert_one(new_user)
    return {"message": "User created successfully.", "email": email_clean}


@app.post("/login")
async def login(request: LoginRequest):
    users = get_users_collection()
    email_clean = request.email.strip().lower()

    user = await users.find_one({"email": email_clean})
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(email=user["email"])
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me")
async def get_my_profile(current_user_email: str = Depends(get_current_user_email)):
    users = get_users_collection()
    email_clean = current_user_email.strip().lower()
    user = await users.find_one({"email": email_clean})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    uploads = get_uploads_collection()
    upload_count = await uploads.count_documents({"user_id": email_clean})

    created_at = user.get("created_at") or user.get("created_date") or datetime.now(timezone.utc).strftime("%B %d, %Y")
    if isinstance(created_at, datetime):
        created_at = created_at.strftime("%B %d, %Y")

    return {
        "email": user["email"],
        "created_at": str(created_at),
        "document_count": upload_count,
    }


@app.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    users = get_users_collection()
    email_clean = current_user_email.strip().lower()
    user = await users.find_one({"email": email_clean})
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=404, detail="User not found or password not set.")

    if not verify_password(request.old_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    if request.old_password == request.new_password:
        raise HTTPException(
            status_code=400, detail="New password must be different from current password."
        )

    new_hashed = hash_password(request.new_password)
    await users.update_one(
        {"email": email_clean}, {"$set": {"hashed_password": new_hashed}}
    )

    return {"message": "Password changed successfully."}


@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user_email: str = Depends(get_current_user_email),
):
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    filename = file.filename or "uploaded_file.pdf"
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    upload_record = Upload(
        filename=filename,
        file_type=file.content_type or "application/pdf",
        user_id=current_user_email.strip().lower(),
        status="Processing",
    )

    uploads = get_uploads_collection()
    result = await uploads.insert_one(upload_record.model_dump())
    inserted_id = getattr(result, "inserted_id", None)

    background_tasks.add_task(
        process_file_ingestion,
        file_id=inserted_id,
        filename=filename,
        user_id=current_user_email.strip().lower(),
    )

    return {
        "message": "File uploaded successfully and ingestion pipeline started.",
        "filename": upload_record.filename,
        "status": upload_record.status,
    }


@app.get("/uploads")
async def get_uploads(current_user_email: str = Depends(get_current_user_email)):
    uploads = get_uploads_collection()
    email_clean = current_user_email.strip().lower()

    user_uploads = []
    cursor = uploads.find({"user_id": email_clean})

    async for document in cursor:
        upload_date = document.get("upload_date")
        if isinstance(upload_date, datetime):
            upload_date = upload_date.isoformat()
        user_uploads.append({
            "id": str(document["_id"]),
            "filename": document.get("filename", ""),
            "upload_date": upload_date,
            "file_type": document.get("file_type", "application/pdf"),
            "status": document.get("status", "Processing"),
        })

    return user_uploads


@app.delete("/uploads/{upload_id}")
async def delete_upload(
    upload_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    uploads = get_uploads_collection()
    email_clean = current_user_email.strip().lower()

    try:
        search_query = {"_id": ObjectId(upload_id), "user_id": email_clean}
    except Exception:
        search_query = {"_id": upload_id, "user_id": email_clean}

    upload_doc = await uploads.find_one(search_query)
    if not upload_doc:
        upload_doc = await uploads.find_one({"_id": upload_id, "user_id": email_clean})
        if upload_doc:
            search_query = {"_id": upload_id, "user_id": email_clean}

    if not upload_doc:
        raise HTTPException(status_code=404, detail="Upload not found")

    filename = upload_doc.get("filename")
    if filename:
        file_path = os.path.join(UPLOAD_DIRECTORY, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Could not remove file {file_path}: {e}")

    await uploads.delete_one(search_query)
    return {"message": "Upload deleted successfully"}


@app.get("/uploads/{upload_id}/preview")
async def get_document_preview(
    upload_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    uploads = get_uploads_collection()
    email_clean = current_user_email.strip().lower()

    try:
        search_query = {"_id": ObjectId(upload_id), "user_id": email_clean}
    except Exception:
        search_query = {"_id": upload_id, "user_id": email_clean}

    upload_doc = await uploads.find_one(search_query)
    if not upload_doc:
        upload_doc = await uploads.find_one({"_id": upload_id, "user_id": email_clean})

    if not upload_doc:
        raise HTTPException(status_code=404, detail="Upload not found")

    filename = upload_doc.get("filename", "")
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    file_size = None
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        file_size = f"{size_bytes / (1024 * 1024):.2f} MB"

    page_count = None
    word_count = None
    if filename.lower().endswith(".pdf") and os.path.exists(file_path):
        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            if text.strip():
                word_count = len(text.split())
        except Exception:
            pass

    file_type = filename.split(".")[-1].upper() if "." in filename else "FILE"
    upload_date = upload_doc.get("upload_date")
    if isinstance(upload_date, datetime):
        upload_date = upload_date.isoformat()

    return {
        "id": str(upload_doc["_id"]),
        "filename": filename,
        "upload_date": upload_date,
        "status": upload_doc.get("status", "Processing"),
        "file_size": file_size,
        "page_count": page_count,
        "word_count": word_count,
        "file_type": file_type,
    }


@app.post("/chat-history")
async def save_chat_message(
    message: dict,
    current_user_email: str = Depends(get_current_user_email),
):
    """Save one chat message (either a user question or an assistant answer)."""
    chat_history = get_chat_history_collection()
    email_clean = current_user_email.strip().lower()

    record = ChatMessage(
        user_id=email_clean,
        role=message.get("role", "user"),
        content=message.get("content", ""),
        sources=message.get("sources"),
        timing=message.get("timing"),
    )

    await chat_history.insert_one(record.model_dump())
    return {"message": "saved"}


@app.get("/chat-history")
async def get_chat_history(current_user_email: str = Depends(get_current_user_email)):
    """Return this user's past conversation, oldest first."""
    chat_history = get_chat_history_collection()
    email_clean = current_user_email.strip().lower()
    cursor = chat_history.find({"user_id": email_clean}).sort("timestamp", 1)

    messages = []
    async for doc in cursor:
        ts = doc.get("timestamp")
        if isinstance(ts, datetime):
            ts = ts.isoformat()
        messages.append({
            "role": doc.get("role"),
            "content": doc.get("content"),
            "sources": doc.get("sources"),
            "timing": doc.get("timing"),
            "timestamp": ts,
        })

    return messages


@app.delete("/chat-history")
async def clear_chat_history(current_user_email: str = Depends(get_current_user_email)):
    """Delete this user's entire conversation history."""
    chat_history = get_chat_history_collection()
    email_clean = current_user_email.strip().lower()
    await chat_history.delete_many({"user_id": email_clean})
    return {"message": "cleared"}


@app.post("/quiz-results")
async def save_quiz_results(
    request: QuizResultRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    """Save quiz results for the current user."""
    quiz_results = get_quiz_results_collection()
    email_clean = current_user_email.strip().lower()

    saved_count = 0
    for result in request.results:
        record = QuizResult(
            user_id=email_clean,
            question_id=str(result.get("question_id", "")),
            topic=result.get("topic", "General"),
            selected_answer=str(result.get("selected_answer", "")),
            correct_answer=str(result.get("correct_answer", "")),
            is_correct=bool(result.get("is_correct", False)),
        )
        await quiz_results.insert_one(record.model_dump())
        saved_count += 1

    return {"message": f"Saved {saved_count} quiz results"}


@app.get("/quiz-results")
async def get_quiz_results(current_user_email: str = Depends(get_current_user_email)):
    """Return this user's quiz history."""
    quiz_results = get_quiz_results_collection()
    email_clean = current_user_email.strip().lower()
    cursor = quiz_results.find({"user_id": email_clean})

    results = []
    async for doc in cursor:
        dt = doc.get("date_taken")
        if isinstance(dt, datetime):
            dt = dt.isoformat()
        results.append({
            "id": str(doc.get("_id", "")),
            "question_id": doc.get("question_id"),
            "topic": doc.get("topic"),
            "selected_answer": doc.get("selected_answer"),
            "correct_answer": doc.get("correct_answer"),
            "is_correct": doc.get("is_correct"),
            "date_taken": dt,
        })

    return results


@app.get("/quiz-results/{user_id}")
async def get_quiz_results_by_user_id(
    user_id: str,
    x_internal_key: str = Header(None),
):
    """Return quiz history for a specific user (internal service access only)."""
    verify_internal_service_key(x_internal_key)

    quiz_results = get_quiz_results_collection()
    cursor = quiz_results.find({"user_id": user_id.strip().lower()})

    results = []
    async for doc in cursor:
        dt = doc.get("date_taken")
        if isinstance(dt, datetime):
            dt = dt.isoformat()
        results.append({
            "id": str(doc.get("_id", "")),
            "question_id": doc.get("question_id"),
            "topic": doc.get("topic"),
            "selected_answer": doc.get("selected_answer"),
            "correct_answer": doc.get("correct_answer"),
            "is_correct": doc.get("is_correct"),
            "date_taken": dt,
        })

    return results