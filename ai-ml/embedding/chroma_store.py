"""
Shared ChromaDB store for the ingestion pipeline.
Uses the same persistent path, collection name, and embedding model
as the chatbot (Team Mu) so ingested chunks are retrievable by it.
"""
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

DEFAULT_CHROMA_PATH = os.getenv(
    "CHROMA_DB_PATH",
    r"C:\Dev\QuantumLearningWorkspace\shared_chroma_data",
)
DEFAULT_COLLECTION_NAME = "study_chunks"
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(DEFAULT_MODEL_NAME)
    return _model


def get_collection(name: str = DEFAULT_COLLECTION_NAME, path: str = None):
    client = chromadb.PersistentClient(path=path or DEFAULT_CHROMA_PATH)
    return client.get_or_create_collection(name=name)


def store_chunks(chunks: list[dict], user_id: str, document_id: str, title: str) -> int:
    """
    Embed and store chunks in the shared ChromaDB collection.

    chunks: list of dicts from chunker.chunk_document(), each with a "text" key.
    Returns the number of chunks stored.
    """
    if not chunks:
        return 0

    collection = get_collection()
    model = get_embedding_model()

    ids = [f"{document_id}_chunk{c['chunk_index']}" for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "user_id": user_id,
            "document_id": document_id,
            "document": title,
            "chunk_index": c["chunk_index"],
        }
        for c in chunks
    ]
    embeddings = model.encode(documents).tolist()

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    return len(chunks)
