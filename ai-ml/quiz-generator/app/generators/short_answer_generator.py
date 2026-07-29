import json
from groq import Groq
from quiz_generator.app.generators.base_generator import BaseGenerator
from quiz_generator.app.config import GROQ_API_KEY, GROQ_MODEL

class ShortAnswerGenerator(BaseGenerator):
    """
    Generator responsible for creating Short Answer questions
    from the provided text using the Groq API, returning structured JSON.
    """

    def __init__(self):
        """
        Initialize the Groq client.
        """
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(self, text: str):
        """
        Generate Short Answer questions using the Groq API.
        Returns a list of dictionaries.
        """

        # Prompt updated for strict JSON output with a root key "questions"
        prompt = f"""
Generate 5 Short Answer questions based on the text below.
Return the result ONLY as a JSON object with a key "questions" containing an array.

JSON Schema:
{{
  "questions": [
    {{
      "question": "The factual question based on the text.",
      "answer": "A concise, accurate answer (1-10 words)."
    }}
  ]
}}

Rules:
- Generate exactly 5 questions.
- Each question must be factual and answerable directly from the text.
- Questions should cover different concepts.
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
            # CRITICAL: Tells Groq to strictly output JSON
            response_format={"type": "json_object"} 
        )

        # 1. Get the raw string content from the LLM
        raw_content = response.choices[0].message.content
        
        # 2. Convert string to Python dictionary and return the list
        try:
            parsed_data = json.loads(raw_content)
            return parsed_data.get("questions", [])
        except json.JSONDecodeError:
            print("Error: Could not parse Short Answer LLM response as JSON.")
            return []