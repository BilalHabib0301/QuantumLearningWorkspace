import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# Groq Configuration
# ==========================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GROQ_MODEL = "openai/gpt-oss-120b"
# NOTE: llama-3.3-70b-versatile has been deprecated by Groq and no
# longer resolves (404 model_not_found). openai/gpt-oss-120b is
# Groq's current recommended general-purpose/reasoning replacement
# as of this writing. This was silently breaking all live quiz
# generation (MCQ, true/false, fill-blank, short-answer all share
# this config) until fixed.


# ==========================================
# YAKE Configuration
# ==========================================

YAKE_MAX_KEYWORDS = 15
YAKE_NGRAM_SIZE = 2
YAKE_DEDUP_THRESHOLD = 0.9


# ==========================================
# Quiz Configuration
# ==========================================

DEFAULT_QUESTION_COUNT = 10

SUPPORTED_QUESTION_TYPES = [
    "mcq",
    "true_false",
    "fill_blank",
    "short_answer"
]