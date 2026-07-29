import json
from groq import Groq
from quiz_generator.app.generators.base_generator import BaseGenerator
from quiz_generator.app.config import GROQ_API_KEY, GROQ_MODEL
class TrueFalseGenerator(BaseGenerator):
    """
    Generator responsible for creating True/False questions
    from the provided text using the Groq API, returning structured JSON.
    """

    def __init__(self):
        """
        Initialize the Groq client.
        """
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(self, text: str):
        """
        Generate True/False questions using the Groq API.
        Returns a list of dictionaries.
        """

        # Prompt updated for strict JSON output with a root key "questions"
        prompt = f"""
Generate 5 True/False questions based on the text below.
Return the result ONLY as a JSON object with a key "questions" containing an array.

JSON Schema:
{{
  "questions": [
    {{
      "question": "A statement that is either true or false based on the text.",
      "answer": "True" or "False"
    }}
  ]
}}

Rules:
- Generate exactly 5 questions.
- Each question must be a clear statement followed by the correct answer ("True" or "False").
- Mix the distribution of True and False answers.
- Questions should cover different concepts from the text.
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
            # CRITICAL: Ensures the response is valid JSON
            response_format={"type": "json_object"} 
        )

        # 1. Get raw string from response
        raw_content = response.choices[0].message.content
        
        # 2. Convert to Python list and return
        try:
            parsed_data = json.loads(raw_content)
            return parsed_data.get("questions", [])
        except json.JSONDecodeError:
            print("Error: Could not parse True/False LLM response as JSON.")
            return []