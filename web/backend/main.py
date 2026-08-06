import os
import shutil
import asyncio
from typing import Optional
from bson import ObjectId

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from models import SignupRequest, LoginRequest, Upload
from database import get_users_collection, get_uploads_collection
from auth_utils import hash_password, verify_password, create_access_token, get_current_user_email
from routes.chat import router as chat_router
from pypdf import PdfReader

app = FastAPI(title="StudyMind AI Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

UPLOAD_DIRECTORY = "uploaded_files"


async def process_file_ingestion(file_id, filename: str, user_id: str):
    """Background task simulating ingestion pipeline (parsing, chunking, embedding)."""
    await asyncio.sleep(4)  # Simulate ingestion progress from pipeline
    uploads = get_uploads_collection()
    query = {"user_id": user_id}
    if file_id:
        try:
            query["_id"] = ObjectId(str(file_id))
        except Exception:
            query["filename"] = filename
    else:
        query["filename"] = filename

    await uploads.update_one(query, {"$set": {"status": "Ready"}})


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
