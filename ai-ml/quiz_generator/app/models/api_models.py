from pydantic import BaseModel, Field


class GenerateQuizRequest(BaseModel):
    """Request body for POST /generate-quiz."""

    topic: str = Field(..., min_length=1, description="Topic to generate the quiz from.")
    question_count: int = Field(
        default=5, ge=1, le=20, description="Number of questions to generate."
    )
    quiz_type: str = Field(
        ...,
        description="One of: mcq, true_false, fill_blank, short_answer.",
    )


class GenerateQuizResponse(BaseModel):
    """Response body for POST /generate-quiz."""

    success: bool
    message: str
    questions: list[dict] = Field(default_factory=list)
    answers: list[dict] = Field(default_factory=list)