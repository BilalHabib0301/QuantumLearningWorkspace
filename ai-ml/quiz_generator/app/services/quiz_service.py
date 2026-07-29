import sys
import os

# This ensures Python can find the 'embedding' folder even though it's a sibling
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Change these lines:
from quiz_generator.app.generators.mcq_generator import MCQGenerator
from quiz_generator.app.generators.true_false_generator import TrueFalseGenerator
from quiz_generator.app.generators.fill_blank_generator import FillBlankGenerator
from quiz_generator.app.generators.short_answer_generator import ShortAnswerGenerator

from embedding.embedder import Embedder 

class QuizService:
    def __init__(self):
        # Initialize the embedder (which connects to Pinecone and MongoDB)
        self.embedder = Embedder()
        
        self.generators = {
            "mcq": MCQGenerator(),
            "true_false": TrueFalseGenerator(),
            "fill_blank": FillBlankGenerator(),
            "short_answer": ShortAnswerGenerator(),
        }

    def generate_quiz_from_topic(self, topic: str, question_type: str, top_k: int = 3):
        """
        1. Searches the Vector Store for the topic.
        2. Retrieves actual text from MongoDB.
        3. Generates the quiz based on that real data.
        """
        # Search for context using the topic
        search_results = self.embedder.search(topic, top_k=top_k)
        
        if not search_results:
            return {"error": f"No data found in your database for: {topic}"}

        # Combine the text from the chunks found in MongoDB
        context_text = "\n\n".join([res['text'] for res in search_results])
        
        # Generate the quiz using our new JSON generators
        return self.generate_quiz(context_text, question_type)

    def generate_quiz(self, text: str, question_type: str):
        """Standard generation from provided text."""
        if question_type not in self.generators:
            raise ValueError(f"Unsupported question type: {question_type}")

        return self.generators[question_type].generate(text)