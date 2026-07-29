
# 1. Import the specific AI Generators
from quiz_generator.app.generators.mcq_generator import MCQGenerator
from quiz_generator.app.generators.true_false_generator import TrueFalseGenerator
from quiz_generator.app.generators.fill_blank_generator import FillBlankGenerator
from quiz_generator.app.generators.short_answer_generator import ShortAnswerGenerator

# 2. THE BRIDGE: Import the Embedder from your sibling folder
from embedding.embedder import Embedder 

class QuizService:
    """
    The Bridge Service:
    Links the Vector Store (Memory) with the AI Generators (Logic).
    """

    def __init__(self):
        # Initialize the Embedder to search Pinecone and MongoDB
        self.embedder = Embedder()
        
        # Initialize the AI Generators
        self.generators = {
            "mcq": MCQGenerator(),
            "true_false": TrueFalseGenerator(),
            "fill_blank": FillBlankGenerator(),
            "short_answer": ShortAnswerGenerator(),
        }

    def generate_quiz_from_topic(self, topic: str, question_type: str, top_k: int = 3):
        """
        RAG PIPELINE (The Bridge in action):
        1. Search: Finds relevant text chunks in the Vector Store.
        2. Retrieve: Fetches full text from MongoDB.
        3. Generate: Feeds that specific text to the LLM to get JSON questions.
        """
        
        # A. Search for context based on the user's topic
        # This returns: [{"text": "...", "score": 0.9}, ...]
        search_results = self.embedder.search(topic, top_k=top_k)
        
        if not search_results:
            return {"error": f"No relevant information found in your database for topic: '{topic}'"}

        # B. Combine all found text chunks into one context paragraph
        context_text = "\n\n".join([res['text'] for res in search_results])
        
        # C. Generate the quiz questions using the found text
        # This will return a clean JSON list/array
        return self.generate_quiz(context_text, question_type)

    def generate_quiz(self, text: str, question_type: str):
        """
        Selects the correct generator and returns the generated JSON.
        """
        if question_type not in self.generators:
            raise ValueError(f"Unsupported question type: {question_type}. Use: mcq, true_false, fill_blank, or short_answer")

        # Calls the .generate() method of the chosen generator
        return self.generators[question_type].generate(text)