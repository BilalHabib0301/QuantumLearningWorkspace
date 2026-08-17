import os
import shutil
import asyncio
from typing import Optional
from bson import ObjectId

from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from datetime import datetime

from pypdf import PdfReader
from models import SignupRequest, LoginRequest, Upload, ChatMessage, ChangePasswordRequest,QuizResult, QuizResultRequest
from database import get_users_collection, get_uploads_collection, get_chat_history_collection,get_quiz_results_collection
from auth_utils import hash_password, verify_password, create_access_token, get_current_user_email, verify_internal_service_key
from routes.chat import router as chat_router
from routes.oauth import router as oauth_router
import httpx

app = FastAPI(title="StudyMind AI Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(oauth_router)

UPLOAD_DIRECTORY = "uploaded_files"
async def process_file_ingestion(file_id, filename: str, user_id: str):
    """Forward the uploaded file to Team Lambda's ingestion service for real chunking + embedding."""
    uploads = get_uploads_collection()
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    new_status = "Ready"
    try:
        with open(file_path, "rb") as f:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "http://127.0.0.1:8001/ingest/pdf",  
                    files={"file": (filename, f, "application/pdf")},
                    data={"user_id": user_id},
                )
        if response.status_code != 200:
            new_status = "Failed"
    except Exception:
        new_status = "Failed"

    query = {"user_id": user_id}
    if file_id:
        try:
            query["_id"] = ObjectId(str(file_id))
        except Exception:
            query["filename"] = filename
    else:
        query["filename"] = filename

    await uploads.update_one(query, {"$set": {"status": new_status}})

# async def process_file_ingestion(file_id, filename: str, user_id: str):
#     """Background task simulating ingestion pipeline (parsing, chunking, embedding)."""
#     await asyncio.sleep(4)  # Simulate ingestion progress from pipeline
#     uploads = get_uploads_collection()
#     query = {"user_id": user_id}
#     if file_id:
#         try:
#             query["_id"] = ObjectId(str(file_id))
#         except Exception:
#             query["filename"] = filename
#     else:
#         query["filename"] = filename

#     await uploads.update_one(query, {"$set": {"status": "Ready"}})


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/signup")
async def signup(request: SignupRequest):
    users = get_users_collection()

    existing_user = await users.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed = hash_password(request.password)

    new_user = {
        "email": request.email,
        "hashed_password": hashed,
        "created_at": datetime.utcnow().strftime("%B %d, %Y"),
    }

    await users.insert_one(new_user)

    return {"message": "User created successfully.", "email": request.email}


@app.post("/login")
async def login(request: LoginRequest):
    users = get_users_collection()

    user = await users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(email=user["email"])

    return {"access_token": token, "token_type": "bearer"}


@app.get("/me")
async def get_my_profile(current_user_email: str = Depends(get_current_user_email)):
    users = get_users_collection()
    user = await users.find_one({"email": current_user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    uploads = get_uploads_collection()
    upload_count = await uploads.count_documents({"user_id": current_user_email})

    created_at = user.get("created_at") or user.get("created_date") or "July 2026"
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
    user = await users.find_one({"email": current_user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if not verify_password(request.old_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    if request.old_password == request.new_password:
        raise HTTPException(
            status_code=400, detail="New password must be different from current password."
        )

    new_hashed = hash_password(request.new_password)
    await users.update_one(
        {"email": current_user_email}, {"$set": {"hashed_password": new_hashed}}
    )

    return {"message": "Password changed successfully."}


@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user_email: str = Depends(get_current_user_email),
):
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    upload_record = Upload(
        filename=file.filename,
        file_type=file.content_type,
        user_id=current_user_email,
        status="Processing",
    )

    uploads = get_uploads_collection()
    result = await uploads.insert_one(upload_record.model_dump())
    inserted_id = getattr(result, "inserted_id", None)

    background_tasks.add_task(
        process_file_ingestion,
        file_id=inserted_id,
        filename=file.filename,
        user_id=current_user_email,
    )

    return {
        "message": "File uploaded successfully and ingestion pipeline started.",
        "filename": upload_record.filename,
        "status": upload_record.status,
    }


@app.get("/uploads")
async def get_uploads(current_user_email: str = Depends(get_current_user_email)):
    uploads = get_uploads_collection()

    user_uploads = []
    cursor = uploads.find({"user_id": current_user_email})

    async for document in cursor:
        user_uploads.append({
            "id": str(document["_id"]),
            "filename": document["filename"],
            "upload_date": document["upload_date"],
            "file_type": document["file_type"],
            "status": document.get("status", "Processing"),
        })

    return user_uploads


@app.delete("/uploads/{upload_id}")
async def delete_upload(
    upload_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    uploads = get_uploads_collection()

    try:
        search_query = {"_id": ObjectId(upload_id), "user_id": current_user_email}
    except Exception:
        search_query = {"_id": upload_id, "user_id": current_user_email}

    upload_doc = await uploads.find_one(search_query)

    if not upload_doc:
        raise HTTPException(status_code=404, detail="Upload not found")

    file_path = os.path.join(UPLOAD_DIRECTORY, upload_doc["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)

    await uploads.delete_one(search_query)

    return {"message": "Upload deleted successfully"}

@app.get("/uploads/{upload_id}/preview")
async def get_document_preview(
    upload_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    uploads = get_uploads_collection()

    try:
        search_query = {"_id": ObjectId(upload_id), "user_id": current_user_email}
    except Exception:
        search_query = {"_id": upload_id, "user_id": current_user_email}

    upload_doc = await uploads.find_one(search_query)

    if not upload_doc:
        raise HTTPException(status_code=404, detail="Upload not found")

    filename = upload_doc["filename"]
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    # File size (in MB, human readable)
    file_size = None
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        file_size = f"{size_bytes / (1024 * 1024):.2f} MB"

    # Page count + word count (PDFs only, best-effort — never break the request)
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
            # Scanned/corrupted PDF or extraction failure — leave as None,
            # frontend will show a placeholder instead of crashing.
            pass

    file_type = filename.split(".")[-1].upper() if "." in filename else "FILE"

    return {
        "id": str(upload_doc["_id"]),
        "filename": filename,
        "upload_date": upload_doc["upload_date"],
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

    record = ChatMessage(
        user_id=current_user_email,
        role=message.get("role"),
        content=message.get("content"),
        sources=message.get("sources"),
    )

    await chat_history.insert_one(record.model_dump())
    return {"message": "saved"}


@app.get("/chat-history")
async def get_chat_history(current_user_email: str = Depends(get_current_user_email)):
    """Return this user's past conversation, oldest first."""
    chat_history = get_chat_history_collection()
    cursor = chat_history.find({"user_id": current_user_email}).sort("timestamp", 1)

    messages = []
    async for doc in cursor:
        messages.append({
            "role": doc["role"],
            "content": doc["content"],
            "sources": doc.get("sources"),
            "timestamp": doc["timestamp"],
        })

    return messages


@app.delete("/chat-history")
async def clear_chat_history(current_user_email: str = Depends(get_current_user_email)):
    """Delete this user's entire conversation history."""
    chat_history = get_chat_history_collection()
    await chat_history.delete_many({"user_id": current_user_email})
    return {"message": "cleared"}

@app.post("/quiz-results")
async def save_quiz_results(
    request: QuizResultRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    """Save quiz results for the current user."""
    quiz_results = get_quiz_results_collection()
    
    for result in request.results:
        record = QuizResult(
            user_id=current_user_email,
            question_id=result.get("question_id"),
            topic=result.get("topic"),
            selected_answer=result.get("selected_answer"),
            correct_answer=result.get("correct_answer"),
            is_correct=result.get("is_correct"),
        )
        await quiz_results.insert_one(record.model_dump())
    
    return {"message": f"Saved {len(request.results)} quiz results"}


@app.get("/quiz-results")
async def get_quiz_results(current_user_email: str = Depends(get_current_user_email)):
    """Return this user's quiz history."""
    quiz_results = get_quiz_results_collection()
    cursor = quiz_results.find({"user_id": current_user_email})
    
    results = []
    async for doc in cursor:
        results.append({
            "question_id": doc.get("question_id"),
            "topic": doc.get("topic"),
            "selected_answer": doc.get("selected_answer"),
            "correct_answer": doc.get("correct_answer"),
            "is_correct": doc.get("is_correct"),
            "date_taken": doc.get("date_taken"),
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
    cursor = quiz_results.find({"user_id": user_id})
    
    results = []
    async for doc in cursor:
        results.append({
            "question_id": doc.get("question_id"),
            "topic": doc.get("topic"),
            "selected_answer": doc.get("selected_answer"),
            "correct_answer": doc.get("correct_answer"),
            "is_correct": doc.get("is_correct"),
            "date_taken": doc.get("date_taken"),
        })
    
    return results