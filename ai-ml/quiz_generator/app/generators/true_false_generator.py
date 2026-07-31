from groq import Groq

from quiz_generator.app.generators.base_generator import BaseGenerator
from quiz_generator.app.config import GROQ_API_KEY, GROQ_MODEL


class TrueFalseGenerator(BaseGenerator):
    """
    Generator responsible for creating True/False questions
    from the provided text using the Groq API.
    """

    def __init__(self):
        """
        Initialize the Groq client.
        """
        self.client = Groq(api_key=GROQ_API_KEY)
        
    def generate(self, text: str):
        """
        Generate True/False questions using the Groq API.
        """

        prompt = f"""
        Generate 5 True/False questions from the following text.

        Rules:
        - Generate exactly 5 questions.
        - Each question must have only two options: True and False.
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
