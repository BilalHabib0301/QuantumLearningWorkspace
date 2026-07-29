import json
from groq import Groq
from quiz_generator.app.generators.base_generator import BaseGenerator
from quiz_generator.app.config import GROQ_API_KEY, GROQ_MODEL

class FillBlankGenerator(BaseGenerator):
    """
    Generator responsible for creating Fill in the Blank questions
    from the provided text using the Groq API, returning structured JSON.
    """

    def __init__(self):
        """
        Initialize the Groq client.
        """
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(self, text: str):
        """
        Generate Fill in the Blank questions using the Groq API.
        Returns a list of dictionaries.
        """

        # Prompt updated for strict JSON output
        prompt = f"""
Generate 5 Fill in the Blank questions based on the text below.
Return the result ONLY as a JSON object with a key "questions" containing an array.

JSON Schema:
{{
  "questions": [
    {{
      "question": "The sentence with exactly one blank represented as '_____'.",
      "answer": "The specific word or phrase that fills the blank."
    }}
  ]
}}

Rules:
- Generate exactly 5 questions.
- Replace only one key concept/term per question with '_____'.
- Questions should cover different parts of the text.
- Difficulty: Medium.

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
            temperature=0.5,
            # CRITICAL: Forces Groq to output valid JSON
            response_format={"type": "json_object"} 
        )

        # 1. Get the raw string content
        raw_content = response.choices[0].message.content
        
        # 2. Convert string to Python dictionary
        try:
            parsed_data = json.loads(raw_content)
            # 3. Return only the list of questions
            return parsed_data.get("questions", [])
        except json.JSONDecodeError:
            print("Error: Could not parse LLM response as JSON.")
            return []