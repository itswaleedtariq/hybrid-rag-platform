# HybridDocs AI

Complete full-stack **hybrid RAG platform** for Project 6 from the uploaded AI Engineering Projects guide.
Users can register, upload private documents, index them, ask questions, inspect retrieved chunks,
and receive grounded answers with inline citations.

## Stack

- FastAPI + SQLModel + SQLite
- ChromaDB dense vector search
- Sentence Transformers embeddings
- BM25 sparse keyword search
- Reciprocal Rank Fusion (RRF)
- CrossEncoder reranking
- Groq chat completions
- React + Vite frontend
- Docker Compose and GitHub Actions

## Features

- Multi-user JWT authentication
- Per-user document/vector isolation
- PDF, DOCX, TXT, Markdown, and HTML ingestion
- Fixed, recursive, and semantic chunking
- SHA-256 file deduplication and near-duplicate chunk removal
- Dense, BM25, and hybrid retrieval modes
- RRF fusion and optional reranking
- Inline citations and heuristic citation validation
- Confidence breakdown
- Retrieval inspector
- Conversation history API
- Starter evaluation dataset and script
- Responsive user interface

## Run locally

### 1. Backend

```bash
cd backend
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install and configure:

```bash
pip install -r requirements.txt
cp .env.example .env
```

Put your Groq key in `backend/.env`:

```env
GROQ_API_KEY=your_key_here
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Open API docs at `http://localhost:8000/docs`.

The first request can be slower while embedding/reranking models download.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`.

## Run with Docker

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_key_here
JWT_SECRET_KEY=replace-with-a-long-random-secret
GROQ_MODEL=llama-3.3-70b-versatile
```

Then run:

```bash
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Seed demo data

```bash
cd backend
python -m scripts.seed_demo
```

Demo account:

```text
Email: demo@example.com
Password: DemoPassword123!
```

## Evaluate

After seeding:

```bash
cd backend
python -m scripts.evaluate
```

The script writes `evaluation_report.json`. Expand the starter dataset to 50+ manually verified
questions before publishing portfolio accuracy numbers.

## Test

```bash
cd backend
pytest
```

## Main endpoints

```text
POST   /api/auth/register
POST   /api/auth/login
GET    /api/auth/me
POST   /api/documents/upload
GET    /api/documents
POST   /api/documents/{id}/reindex
DELETE /api/documents/{id}
POST   /api/chat/ask
GET    /api/chat/conversations
GET    /api/chat/conversations/{id}
DELETE /api/chat/conversations/{id}
GET    /api/stats
GET    /api/health
```

## Production upgrades

For public deployment, use PostgreSQL, server-backed Chroma or Qdrant, S3-compatible object
storage, a background ingestion queue, HTTPS, rate limiting, email verification, and database
migrations. Local Chroma `PersistentClient` is appropriate for development and portfolio demos.

## Push to GitHub

```bash
git init
git add .
git commit -m "Build hybrid RAG platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/hybrid-rag-platform.git
git push -u origin main
```

## License

MIT
