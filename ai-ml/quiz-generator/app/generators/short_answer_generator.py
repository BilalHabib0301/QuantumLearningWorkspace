from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.generators.base_generator import BaseGenerator


class ShortAnswerGenerator(BaseGenerator):
    """
    Generator responsible for creating Short Answer questions
    from the provided text using the Groq API.
    """

    def __init__(self):
        """
        Initialize the Groq client.
        """
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(self, text: str):
        """
        Generate Short Answer questions using the Groq API.
        """

        prompt = f"""
        Generate 5 short answer questions from the following text.

        Rules:
        - Generate exactly 5 questions.
        - Each question should require a short factual answer.
        - Clearly mention the correct answer.
        - Questions should cover different concepts.
        - Keep the difficulty at medium level.

        Text:
        {text}
        """

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5
        )

        return response.choices[0].message.content
