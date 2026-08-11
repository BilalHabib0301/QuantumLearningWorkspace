from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class User(BaseModel):
    email: EmailStr
    hashed_password: str
    created_date: datetime = Field(default_factory=datetime.utcnow)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)

class Upload(BaseModel):
    filename: str = Field(..., min_length=1)
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    file_type: str = Field(..., min_length=1)
    status: str = Field(default="Processing")
    metadata: Optional[dict] = None
    user_id: str

class ChatMessage(BaseModel):
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    sources: Optional[list] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class QuizResult(BaseModel):
    user_id: str
    question_id: str
    topic: str
    selected_answer: str
    correct_answer: str
    is_correct: bool
    date_taken: datetime = Field(default_factory=datetime.utcnow)


class QuizResultRequest(BaseModel):
    results: list  # List of quiz result dicts