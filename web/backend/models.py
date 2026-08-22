from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, EmailStr


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(BaseModel):
    email: EmailStr
    hashed_password: Optional[str] = None
    auth_provider: Optional[str] = None
    created_at: Optional[str] = None
    created_date: datetime = Field(default_factory=utc_now)


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
    upload_date: datetime = Field(default_factory=utc_now)
    file_type: Optional[str] = "application/pdf"
    status: str = Field(default="Processing")
    metadata: Optional[dict] = None
    user_id: str
    document_id: Optional[str] = None
    chunks_stored: Optional[int] = 0
    last_error: Optional[str] = None
    processed_at: Optional[datetime] = None


class ChatMessage(BaseModel):
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    sources: Optional[List[Any]] = None
    timing: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=utc_now)


class QuizResult(BaseModel):
    user_id: str
    question_id: Optional[str] = None
    topic: Optional[str] = "General"
    selected_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    is_correct: bool = False
    date_taken: datetime = Field(default_factory=utc_now)


class QuizResultRequest(BaseModel):
    results: List[Dict[str, Any]] = Field(default_factory=list)


class GenerateQuizProxyRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic to generate the quiz from.")
    question_count: int = Field(default=5, ge=1, le=20, description="Number of questions (1-20).")
    quiz_type: str = Field(..., description="One of: mcq, true_false, fill_blank, short_answer.")


class QuizSubmissionAnswer(BaseModel):
    question_id: str
    selected_answer: Optional[str] = ""


class SubmitQuizRequest(BaseModel):
    quiz_id: Optional[str] = None
    topic: Optional[str] = "General"
    answers: Optional[Any] = None
    results: Optional[List[Dict[str, Any]]] = None



class HistoryMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    filename: Optional[str] = None
    history: Optional[List[HistoryMessage]] = None
    top_k: Optional[int] = 4
    include_sources: Optional[bool] = True
    rerank: Optional[bool] = True
    multi_hop: Optional[bool] = True
    skip_cache: Optional[bool] = False