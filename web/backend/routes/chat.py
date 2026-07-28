from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AskRequest(BaseModel):
    question: str


class Source(BaseModel):
    document: str
    chunk: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@router.post("/ask", response_model=AskResponse)
def mock_ask(request: AskRequest):
    return {
        "answer": "This is a placeholder answer for testing. The real chatbot backend will replace this.",
        "sources": [
            {"document": "sample.pdf", "chunk": "chunk_1"}
        ],
    }