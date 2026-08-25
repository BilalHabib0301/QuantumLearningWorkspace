from datetime import datetime, timezone
from typing import Literal, Optional, List

from pydantic import BaseModel, Field, EmailStr


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Upload(BaseModel):
    filename: str = Field(..., min_length=1)
    upload_date: datetime = Field(default_factory=get_utc_now)
    file_type: str = Field(..., min_length=1)
    status: str = Field(default="uploaded")
    metadata: Optional[dict] = None
    user_id: str


class User(BaseModel):
    email: EmailStr
    hashed_password: str
    created_date: datetime = Field(default_factory=get_utc_now)



class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ==========================================
# Flashcard & Weak-Topic Data Models
# ==========================================

class Flashcard(BaseModel):
    id: str
    front: str
    back: str
    question: str
    answer: str
    topic: str
    difficulty: str = Field(default="medium")
    created_at: datetime = Field(default_factory=get_utc_now)


class GenerateFlashcardsRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic to generate flashcards for")
    num_cards: Optional[int] = Field(default=5, ge=1, le=20, description="Number of cards to generate (1-20)")
    difficulty: Optional[str] = Field(default="medium", description="Difficulty level (easy, medium, hard)")
    content: Optional[str] = Field(default=None, description="Optional raw text / notes to extract flashcards from")


class GenerateFlashcardsResponse(BaseModel):
    success: bool = True
    topic: str
    total_cards: int
    cards: List[Flashcard]


class FlashcardReviewRequest(BaseModel):
    flashcard_id: str = Field(..., min_length=1, description="Unique identifier of the flashcard")
    topic: str = Field(..., min_length=1, description="Topic of the flashcard")
    status: Literal["known", "still_learning"] = Field(..., description="Review status: 'known' or 'still_learning'")
    user_id: Optional[str] = Field(default=None, description="Optional user ID; inferred from auth token if available")


class FlashcardReview(BaseModel):
    user_id: str
    flashcard_id: str
    topic: str
    status: Literal["known", "still_learning"]
    date_reviewed: datetime = Field(default_factory=get_utc_now)
    # Schema alignment with quiz results for weak-topic detection
    item_type: str = Field(default="flashcard", description="Type of learning item: 'flashcard' or 'quiz'")
    is_weak: bool = Field(default=False, description="True if status is 'still_learning' or incorrect")



class WeakTopicSummary(BaseModel):
    topic: str
    total_reviews: int
    known_count: int
    still_learning_count: int
    mastery_score: float
    is_weak: bool


class TopicReviewStatsResponse(BaseModel):
    user_id: str
    weak_topics: List[WeakTopicSummary]
    total_reviews: int
