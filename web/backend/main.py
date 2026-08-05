import os
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware

from models import SignupRequest, LoginRequest, Upload
from database import get_users_collection, get_uploads_collection
from auth_utils import hash_password, verify_password, create_access_token, get_current_user_email
from routes.chat import router as chat_router
from bson import ObjectId

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI(title="StudyMind AI Backend")
app.include_router(chat_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIRECTORY = "uploaded_files"


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
    )

    uploads = get_uploads_collection()
    await uploads.insert_one(upload_record.model_dump())

    return {
        "message": "File uploaded successfully.",
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
            "status": document["status"],
        })

    return user_uploads



@app.delete("/uploads/{upload_id}")
async def delete_upload(
    upload_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    uploads = get_uploads_collection()

    upload_doc = await uploads.find_one({
        "_id": ObjectId(upload_id),
        "user_id": current_user_email,
    })

    if not upload_doc:
        raise HTTPException(status_code=404, detail="Upload not found")

    file_path = os.path.join(UPLOAD_DIRECTORY, upload_doc["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)

    await uploads.delete_one({"_id": ObjectId(upload_id)})

    return {"message": "Upload deleted successfully"}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print("VALIDATION ERROR:")
    print(exc.errors())
    print("BODY:")
    print(exc.body)

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )