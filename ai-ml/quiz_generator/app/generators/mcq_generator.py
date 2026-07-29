import json
import groq
from quiz_generator.app.generators.base_generator import BaseGenerator
from quiz_generator.app.config import GROQ_API_KEY, GROQ_MODEL
class MCQGenerator(BaseGenerator):
    def __init__(self):
        # Initialize the Groq client using your config
        self.client = groq.Groq(api_key=GROQ_API_KEY)

    def generate(self, text: str):
        # 1. Define the updated JSON prompt
        prompt = f"""
        Generate 5 Multiple Choice Questions based on the text below.
        Return the result ONLY as a JSON object with a key named "questions" containing an array of objects.

        JSON Schema:
        {{
          "questions": [
            {{
              "question": "The question text.",
              "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
              "answer": "The correct option text exactly as it appears in the options list."
            }}
          ]
        }}

        Rules:
        - Generate exactly 5 questions.
        - Each question must have exactly 4 unique options.
        - The 'answer' field must contain the text of the correct option.
        - Difficulty: Medium.

        Text:
        {text}
        """

        # 2. Call the Groq API
        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            # This is CRITICAL for Groq to return clean JSON
            response_format={"type": "json_object"} 
        )

        # 3. Parse the string content into a Python dictionary
        raw_output = response.choices[0].message.content
        parsed_json = json.loads(raw_output)

        # 4. Extract the list of questions and return it
        # Because we asked for a "questions" key in the prompt
        if isinstance(parsed_json, dict) and "questions" in parsed_json:
            return parsed_json["questions"]
        
        return parsed_json