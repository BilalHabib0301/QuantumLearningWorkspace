"""
Team Lambda Quiz API — FastAPI service.

Run from ai-ml/ (so the quiz_generator.* and embedding.* imports resolve):
  uvicorn quiz_generator.app.main:app --reload --port 8002

Interactive docs: http://127.0.0.1:8002/docs
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from quiz_generator.app.models.api_models import GenerateQuizRequest, GenerateQuizResponse
from quiz_generator.app.services.quiz_service import QuizService
from quiz_generator.app.auth import get_current_user_id

app = FastAPI(title="StudyMind Quiz API — Team Lambda")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_service: QuizService | None = None


def get_service() -> QuizService:
    global _service
    if _service is None:
        _service = QuizService()
    return _service


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/generate-quiz", response_model=GenerateQuizResponse)
def generate_quiz_endpoint(
    body: GenerateQuizRequest,
    user_id: str = Depends(get_current_user_id),
) -> GenerateQuizResponse:
    """
    [Contract v1, Section 10] Requires "Authorization: Bearer <jwt>".
    user_id is derived from the verified token (never from client
    input) and used to scope retrieval to this user's own content only.
    """
    service = get_service()

    valid_types = {"mcq", "true_false", "fill_blank", "short_answer"}
    if body.quiz_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"quiz_type must be one of: {', '.join(sorted(valid_types))}",
        )

    try:
        result = service.generate_quiz_from_topic(
            topic=body.topic,
            question_type=body.quiz_type,
            user_id=user_id,
            number_of_questions=body.question_count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if "error" in result:
        return GenerateQuizResponse(
            success=False,
            message=result["error"],
            questions=[],
            answers=[],
        )

    return GenerateQuizResponse(
        success=True,
        message=f"Generated {len(result['questions'])} questions.",
        questions=result["questions"],
        answers=result["answers"],
    )