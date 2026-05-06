import os

files = {
    'apps/documents/services/embedding.py': '''import voyageai
from sentence_transformers import SentenceTransformer
from dataclasses import dataclass
from django.conf import settings
import structlog

log = structlog.get_logger()

@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    model_used: str
    dimensions: int  # 1024 for both voyage-law-2 and bge-large


class EmbeddingService:
    """
    Primary:  Voyage AI voyage-law-2 (legal fine-tuned, free 50M tokens)
    Fallback: BAAI/bge-large-en-v1.5 via sentence-transformers (if no key)

    Singleton pattern — model/client loaded once, reused across requests.
    Voyage AI distinguishes query vs document via input_type parameter.
    BGE requires manual prefix for queries.
    """
    _voyage: voyageai.Client | None = None
    _local: SentenceTransformer | None = None

    def _voyage_client(self):
        if not self._voyage and getattr(settings, "VOYAGE_API_KEY", None):
            self._voyage = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        return self._voyage

    def _local_model(self):
        if not self._local:
            log.info("local_embedding_model_loading", model="bge-large-en-v1.5")
            self._local = SentenceTransformer("BAAI/bge-large-en-v1.5")
        return self._local

    def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        """For document chunks at indexing time."""
        client = self._voyage_client()
        if client:
            result = client.embed(texts, model="voyage-law-2",
                                  input_type="document",
                                  truncation=True)
            return EmbeddingResult(result.embeddings, "voyage-law-2", 1024)
        vecs = self._local_model().encode(
            texts, batch_size=32, normalize_embeddings=True).tolist()
        return EmbeddingResult(vecs, "bge-large-en-v1.5", 1024)

    def embed_query(self, query: str) -> list[float]:
        """For semantic search queries at retrieval time."""
        client = self._voyage_client()
        if client:
            result = client.embed([query], model="voyage-law-2",
                                  input_type="query")
            return result.embeddings[0]
        prefix = "Represent this sentence for searching relevant passages: "
        return self._local_model().encode(
            prefix + query, normalize_embeddings=True).tolist()
''',
    
    'README.md': '''# LexAI — AI-Powered Legal Paralegal

An algorithmic paralegal for Indian solo legal practitioners. Processes
FIRs, witness statements, and affidavits to extract patterns, detect
contradictions, and draft verified legal documents.

## Required Services & API Keys

All services below must be configured before running.

| Service | Required | Free Tier | Get It |
|---|---|---|---|
| Anthropic API | YES | No (~$5 credit) | [console.anthropic.com](https://console.anthropic.com) |
| Voyage AI | YES | 50M tokens free | [dash.voyageai.com](https://dash.voyageai.com) |
| Redis | YES | 10K req/day free | [upstash.com](https://upstash.com) |
| PostgreSQL | Prod only | 500MB free | [supabase.com](https://supabase.com) |
| Cloudinary | Prod only | 25GB free | [cloudinary.com](https://cloudinary.com) |
| Vercel | Frontend | 100GB/mo free | [vercel.com](https://vercel.com) |

### Anthropic API
- Used for: Intent classification (Haiku), synthesis, contradiction detection,
  template filling, entailment scoring (Sonnet)
- Estimated cost: $0.02–0.05 per lawyer query with prompt caching enabled
- Get key: https://console.anthropic.com → API Keys

### Voyage AI
- Used for: Embedding legal documents and search queries (voyage-law-2)
- Free tier: 50 million tokens ≈ 12,500 full legal documents at no cost
- Get key: https://dash.voyageai.com → API Keys

### Redis (Upstash recommended)
- Used for: Celery task broker + result backend, SSE pub/sub, query context cache
- Free tier: 10,000 commands/day (sufficient for development and small production)
- Get URL: https://upstash.com → Create Database → Copy Redis URL

### PostgreSQL
- Local dev: SQLite works (default in development.py)
- Production: Supabase free tier (500MB) or Railway
- Get URL: https://supabase.com → Project Settings → Database → Connection String

### Cloudinary (production file storage)
- Used for: Storing uploaded PDFs and generated exports across server restarts
- For hackathon/MVP: skip this, use local filesystem storage (USE_CLOUDINARY=False)
- Get credentials: https://cloudinary.com → Dashboard → API Keys

## Backend Setup

```bash
cp .env.example .env
# Fill in your API keys in .env
pip install -r requirements.txt
python manage.py migrate
celery -A config worker -l info &
python manage.py runserver
```

## Frontend Setup

```bash
cd frontend
cp .env.local.example .env.local
# Set VITE_API_BASE_URL=http://localhost:8000/api/v1
npm install
npm run dev
```

## Deploy Frontend to Vercel

```bash
cd frontend
npm run build        # generates dist/
vercel --prod        # or connect repo to Vercel dashboard
```

Set in Vercel dashboard → Settings → Environment Variables:
  VITE_API_BASE_URL = https://your-backend.railway.app/api/v1

Then update backend .env:
  CORS_ALLOWED_ORIGINS = https://your-lexai-app.vercel.app

## Cost Breakdown (per month, light usage ~200 queries)

| Service | Cost |
|---|---|
| Anthropic (200 queries × $0.04) | ~$8 |
| Voyage AI (within free 50M tokens) | $0 |
| Redis Upstash free tier | $0 |
| Supabase free tier | $0 |
| Vercel free tier | $0 |
| **Total** | **~$8/month** |
''',

    '.env.example': '''# ── Django ────────────────────────────────────────────────
DJANGO_SETTINGS_MODULE=config.settings.development
SECRET_KEY=change-me-generate-with-django-get-random-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# ── Database ──────────────────────────────────────────────
# Dev: leave as SQLite. Prod: use PostgreSQL connection string.
DATABASE_URL=sqlite:///db.sqlite3
# DATABASE_URL=postgresql://user:password@host:5432/lexai_db

# ── Redis (get free instance from upstash.com) ────────────
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ── AI Services ───────────────────────────────────────────
# Anthropic: https://console.anthropic.com → API Keys
ANTHROPIC_API_KEY=sk-ant-api03-...

# Voyage AI: https://dash.voyageai.com → API Keys
# Free tier: 50M tokens on voyage-law-2 (sufficient for ~12,500 legal docs)
VOYAGE_API_KEY=pa-...

# ── Claude Model Config ───────────────────────────────────
CLAUDE_SONNET_MODEL=claude-sonnet-4-6
CLAUDE_HAIKU_MODEL=claude-haiku-4-5-20251001
CLAUDE_HAIKU_MAX_TOKENS=512
CLAUDE_SONNET_MAX_TOKENS=1024
CLAUDE_TEMPERATURE=0.1
CLAUDE_MAX_RETRIES=3

# ── Embedding ─────────────────────────────────────────────
VOYAGE_EMBEDDING_MODEL=voyage-law-2
EMBEDDING_BATCH_SIZE=32

# ── Retrieval ─────────────────────────────────────────────
DEFAULT_TOP_K=8
MIN_RELEVANCE_SCORE=0.38
MAX_CHUNK_TOKENS_PER_CALL=2500

# ── Verification Thresholds ───────────────────────────────
COSINE_VERIFIED_THRESHOLD=0.82
COSINE_HALLUCINATED_THRESHOLD=0.45
PURGE_SCORE_THRESHOLD=0.35
CONTRADICTION_PURGE_THRESHOLD=0.80

# ── Storage ───────────────────────────────────────────────
MEDIA_ROOT=/var/lexai/media
CHROMA_PERSIST_DIR=/var/lexai/chroma
EXPORT_ROOT=/var/lexai/exports
USE_CLOUDINARY=False
# CLOUDINARY_CLOUD_NAME=
# CLOUDINARY_API_KEY=
# CLOUDINARY_API_SECRET=

# ── CORS — add your Vercel URL here ──────────────────────
# Example: CORS_ALLOWED_ORIGINS=http://localhost:5173,https://lexai.vercel.app
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
CORS_ALLOW_CREDENTIALS=True

# ── API Docs ──────────────────────────────────────────────
SHOW_API_DOCS=True
'''

}

for k, v in files.items():
    os.makedirs(os.path.dirname(k) or '.', exist_ok=True)
    with open(k, 'w', encoding='utf-8') as f:
        f.write(v)

print("done")