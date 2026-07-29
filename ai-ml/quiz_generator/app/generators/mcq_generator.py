from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.generators.base_generator import BaseGenerator


class MCQGenerator(BaseGenerator):
    """
    Generator responsible for creating Multiple Choice Questions (MCQs)
    from the provided text using the Groq API.
    """

    def __init__(self):
        """
        Initialize the Groq client.
        """
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(self, text: str):
        """
        Generate Multiple Choice Questions using the Groq API.
        """

        prompt = f"""
        Generate 5 multiple-choice questions from the following text.

        Rules:
        - Each question should have exactly 4 options.
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
