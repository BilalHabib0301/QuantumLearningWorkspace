# StudyMind AI — Ingestion & Embedding Pipeline

This pipeline extracts text from various sources (YouTube, web articles, PDFs), chunks it, embeds it using a local model, and stores the results in **MongoDB** (conversation/document history) and **Pinecone** (vector search).



## Architecture Overview

The pipeline consists of two independent services that run in parallel:

| Service | Role | Command |
|---|---|---|
| **Ingestion Server** | FastAPI server that receives and processes raw content | `uvicorn ingestion.main:app` |
| **Embedding Module** | Chunks text, generates embeddings, and pushes them to MongoDB + Pinecone | `python -m embedding.embedder` |

Data flow: **Source (YouTube / Article / PDF) → Ingestion → Chunking → Embedding → MongoDB + Pinecone**

---

## Prerequisites

Before starting, make sure you have:

- Python 3.9+ installed
- A [MongoDB Atlas](https://www.mongodb.com/atlas) cluster (or local MongoDB instance)
- A [Pinecone](https://www.pinecone.io/) account with an index created
- A [Hugging Face](https://huggingface.co/settings/tokens) account (for model access, if required)

---

## 1. Installation

Open your terminal and navigate to the project root, then into the `ai-ml` directory:

```bash
cd ai-ml
```

**Create and activate a virtual environment** (recommended):

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

---

## 2. Environment Setup

> **⚠️ Important: Never commit real API keys or credentials to GitHub.**
> This project uses a `.env.example` template — copy it locally and fill in your own secrets.

1. Locate the template file at `.env.example`.
2. Copy it and rename the copy to `.env`:

   ```bash
   cp .env.example .env
   ```

3. Open `.env` and fill in your own values:

   | Variable | Description |
   |---|---|
   | `PINECONE_API_KEY` | Your Pinecone API key |
   | `HOST` | Your Pinecone index host URL |
   | `PINECONE_INDEX_NAME` | Name of your Pinecone index |
   | `PINECONE_TOP_K` | Number of top results to retrieve (default: `5`) |
   | `MONGODB_URI` | Your MongoDB Atlas connection string |
   | `HF_TOKEN` | Your Hugging Face access token |

4. Double-check `.env` is listed in `.gitignore` so it's never accidentally pushed:

   ```gitignore
   .env
   ```

---

## 3. Running the Pipeline

Because ingestion and embedding are independent services, you'll need **two separate terminals** running at the same time.

### Terminal 1 — Start the Ingestion Server

```bash
cd ai-ml
python -m uvicorn ingestion.main:app --reload
```

> **Note:** You must use the `python -m` prefix for this to work correctly.

Wait until you see `Application startup complete`, then leave this terminal running.

- Server URL: `http://127.0.0.1:8000`
- Interactive API docs (Swagger UI): `http://127.0.0.1:8000/docs`

### Terminal 2 — Run the Embedding Module

Open a **second terminal**, and make sure you're also in the `ai-ml` folder:

```bash
cd ai-ml
```

With Terminal 1 still running, run the embedder against your desired source type (see examples below).

---

## 4. Usage Examples

Run these from Terminal 2, while the ingestion server (Terminal 1) is active.

**YouTube video:**
```bash
python -m embedding.embedder --youtube "https://youtube.com/watch?v=VIDEO_ID"
```

**Web article:**
```bash
python -m embedding.embedder --article "https://example.com/some-article"
```

**PDF file:**
```bash
python -m embedding.embedder --pdf "C:\path\to\file.pdf"
```

**Quick sanity check** (no external input, uses a hardcoded sample):
```bash
python -m embedding.embedder
```

---

## Troubleshooting

| Issue | Likely Cause / Fix |
|---|---|
| `uvicorn: command not found` | Forgot the `python -m` prefix, or dependencies not installed |
| Connection refused on `127.0.0.1:8000` | Terminal 1 (ingestion server) isn't running |
| Pinecone auth errors | Check `PINECONE_API_KEY` and `HOST` in your `.env` |
| MongoDB connection timeout | Check `MONGODB_URI`, and confirm your IP is whitelisted in MongoDB Atlas Network Access |
| Missing module errors | Re-run `pip install -r requirements.txt` and `pip install -r embedding/requirements.txt` |


