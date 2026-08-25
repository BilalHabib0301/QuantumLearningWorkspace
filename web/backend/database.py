import os
from typing import Optional
import certifi

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "study_mind_db")

client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    """Create and cache the MongoDB client instance."""
    global client
    if client is None:
        client = AsyncIOMotorClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=10000,
    tlsCAFile=certifi.where(),
)
    return client

def get_database():
    """Return the configured database object."""
    return get_client()[MONGODB_DB_NAME]


def get_uploads_collection():
    """Return the uploads collection used by the app."""
    return get_database()["uploads"]

def get_users_collection():
    return get_database()["users"]

def get_flashcard_reviews_collection():
    """Return the flashcard_reviews collection for tracking user reviews."""
    return get_database()["flashcard_reviews"]

def get_flashcards_collection():
    """Return the flashcards collection for saved/generated flashcards."""
    return get_database()["flashcards"]