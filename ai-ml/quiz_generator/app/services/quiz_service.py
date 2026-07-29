from app.generators.mcq_generator import MCQGenerator
from app.generators.true_false_generator import TrueFalseGenerator
from app.generators.fill_blank_generator import FillBlankGenerator
from app.generators.short_answer_generator import ShortAnswerGenerator


class QuizService:
    """
    Service responsible for selecting the appropriate
    quiz generator based on question type.
    """

    def __init__(self):
        self.generators = {
            "mcq": MCQGenerator(),
            "true_false": TrueFalseGenerator(),
            "fill_blank": FillBlankGenerator(),
            "short_answer": ShortAnswerGenerator(),
        }

    def generate_quiz(self, text: str, question_type: str):
        """
        Generate quiz questions based on the selected type.
        """

        if question_type not in self.generators:
            raise ValueError(f"Unsupported question type: {question_type}")

        return self.generators[question_type].generate(text)