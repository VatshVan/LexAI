# LexAI — AI-Powered Legal Paralegal

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

## 🚀 How to Run the Project Locally

To run LexAI locally, you need three separate terminal windows/tabs to run the backend server, the Celery background worker, and the React frontend respectively.

### Step 1: Environment Setup
First, ensure you have your API keys ready (Anthropic, Voyage AI, and an Upstash Redis URL).

1. In the root directory, create your backend `.env` file:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` and fill in your `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, and `REDIS_URL`.*

2. Navigate to the `frontend` directory and create the frontend `.env.local` file:
   ```bash
   cd frontend
   cp .env.local.example .env.local
   ```
   *(Ensure `VITE_API_BASE_URL=http://localhost:8000/api/v1` is set inside `.env.local`)*

### Step 2: Install Dependencies & Migrate Database
In your main terminal, install all backend requirements and set up the SQLite database:
```bash
pip install -r requirements.txt
python manage.py migrate
```

### Step 3: Run the Stack
You will need to open **three separate terminal windows** to keep all services running simultaneously:

**Terminal 1: Django Backend Server**
```bash
# From the root directory
python manage.py runserver
```

**Terminal 2: Celery Task Worker**
```bash
# From the root directory
# Windows users might need to run: celery -A config worker -l info -P eventlet
celery -A config worker -l info
```

**Terminal 3: React Frontend (Vite)**
```bash
# From the root directory
cd frontend
npm install
npm run dev
```

Once all three are running, open your browser and navigate to `http://localhost:5173` (or the port Vite outputs in Terminal 3) to use LexAI!

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
