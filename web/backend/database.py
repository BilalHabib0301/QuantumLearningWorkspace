import os
from typing import Optional, Dict, Any, List
import logging
import certifi
from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("uvicorn")
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "study_mind_db")

client: Optional[AsyncIOMotorClient] = None


class InMemoryCursor:
    """Mock async cursor for in-memory documents."""
    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = docs
        self._iter = iter(docs)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class InMemoryCollection:
    """In-memory collection fallback when MongoDB URI is a placeholder."""
    def __init__(self, name: str):
        self.name = name
        self.documents: List[Dict[str, Any]] = []

    async def find_one(self, query: Dict[str, Any]):
        for doc in self.documents:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                return dict(doc)
        return None

    async def insert_one(self, document: Dict[str, Any]):
        doc = dict(document)
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.documents.append(doc)
        return type("InsertResult", (), {"inserted_id": doc["_id"]})()

    def find(self, query: Optional[Dict[str, Any]] = None):
        if not query:
            return InMemoryCursor([dict(d) for d in self.documents])
        results = []
        for doc in self.documents:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                results.append(dict(doc))
        return InMemoryCursor(results)

    async def delete_one(self, query: Dict[str, Any]):
        for i, doc in enumerate(self.documents):
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                self.documents.pop(i)
                return type("DeleteResult", (), {"deleted_count": 1})()
        return type("DeleteResult", (), {"deleted_count": 0})()

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        set_fields = update.get("$set", {})
        matched_count = 0
        modified_count = 0
        for doc in self.documents:
            match = True
            for k, v in query.items():
                if k == "_id" and isinstance(v, ObjectId):
                    if str(doc.get("_id")) != str(v) and doc.get("_id") != v:
                        match = False
                        break
                elif doc.get(k) != v:
                    match = False
                    break
            if match:
                matched_count += 1
                for field, val in set_fields.items():
                    if doc.get(field) != val:
                        doc[field] = val
                        modified_count += 1
                break
        return type("UpdateResult", (), {"matched_count": matched_count, "modified_count": modified_count})()

    async def count_documents(self, query: Dict[str, Any]):
        count = 0
        for doc in self.documents:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                count += 1
        return count



_in_memory_db: Dict[str, InMemoryCollection] = {
    "users": InMemoryCollection("users"),
    "uploads": InMemoryCollection("uploads"),
    "chat_history": InMemoryCollection("chat_history"),
    "quiz_results": InMemoryCollection("quiz_results"),
}


def is_placeholder_uri(uri: str) -> bool:
    """Check if MongoDB URI is an unconfigured template."""
    return (
        not uri
        or "<username>" in uri
        or "<password>" in uri
        or "<cluster-url>" in uri
    )


def get_client() -> Optional[AsyncIOMotorClient]:
    """Create and cache the MongoDB client instance if configured."""
    global client
    if is_placeholder_uri(MONGODB_URI):
        return None

    if client is None:
        client = AsyncIOMotorClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=10000,
            tlsCAFile=certifi.where(),
        )
    return client


def get_database():
    """Return the configured database object or in-memory fallback."""
    c = get_client()
    if c is None:
        return _in_memory_db
    return c[MONGODB_DB_NAME]


def get_uploads_collection():
    """Return the uploads collection used by the app."""
    db = get_database()
    if isinstance(db, dict):
        return db["uploads"]
    return db["uploads"]

def get_chat_history_collection():
    """Return the chat history collection used by the app."""
    db = get_database()
    if isinstance(db, dict):
        return db["chat_history"]
    return db["chat_history"]

def get_users_collection():
    """Return the users collection used by the app."""
    db = get_database()
    if isinstance(db, dict):
        return db["users"]
    return db["users"]

def get_quiz_results_collection():
    """Return the quiz results collection used by the app."""
    db = get_database()
    if isinstance(db, dict):
        return db["quiz_results"]
    return db["quiz_results"]