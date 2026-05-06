# LexAI

LexAI is an AI-assisted legal drafting and review platform built for handling real-world case documents. It helps ingest PDFs and text files, extract key facts, search across evidence, detect inconsistencies, and generate structured legal outputs.

## What it does

- Ingests case documents such as FIRs, witness statements, affidavits, and related attachments
- Runs OCR on scanned documents when needed
- Classifies user intent and routes requests through the right workflow
- Retrieves relevant evidence from a vector store for grounded responses
- Detects contradictions and supports entailment-style verification
- Drafts and assembles legal content from templates and structured context
- Exports generated work into document formats for downstream use

## Project layout

- Backend: Django + Django REST Framework
- Async processing: Celery + Redis
- Retrieval and embeddings: ChromaDB + Voyage AI
- LLM orchestration: Anthropic Claude
- OCR: PyMuPDF and Tesseract-based support
- Frontend: React + Vite + TypeScript + Tailwind CSS

The backend is organized into domain apps for documents, orchestration, templates, compilation, retrieval, verification, and agent workflows.

## Requirements

- Python 3.10+
- Node.js 18+
- Redis
- API access for the configured AI services

For local development, SQLite is enabled by default. PostgreSQL can be used in production.

## Environment setup

Create the backend environment file:

1. Copy the example file in the project root:
   - `.env.example` to `.env`
2. Fill in the required values, especially:
   - `SECRET_KEY`
   - `ANTHROPIC_API_KEY`
   - `VOYAGE_API_KEY`
   - `REDIS_URL`
3. If you are using the frontend locally, copy the example file in the frontend folder:
   - `frontend/.env.local.example` to `frontend/.env.local`
4. Set `VITE_API_BASE_URL` to your backend URL, for example:
   - `http://localhost:8000/api/v1`

## Installation

From the project root:

1. Install Python dependencies:
   - `pip install -r requirements.txt`
2. Apply database migrations:
   - `python manage.py migrate`
3. Install frontend dependencies:
   - `cd frontend`
   - `npm install`

## Run locally

Run the backend, worker, and frontend in separate terminals.

### 1) Django backend

From the project root:

- `python manage.py runserver`

### 2) Celery worker

From the project root:

- `celery -A config worker -l info`

### 3) Frontend

From the `frontend` folder:

- `npm run dev`

Open the frontend URL shown by Vite, usually `http://localhost:5173`.

## API documentation

If API docs are enabled in the backend settings, the schema and Swagger UI are available at:

- `/api/v1/schema/`
- `/api/v1/schema/ui/`

## Frontend scripts

Available scripts in `frontend/package.json`:

- `npm run dev` — start the Vite development server
- `npm run build` — type-check and build for production
- `npm run preview` — preview the production build locally
- `npm run generate:types` — generate TypeScript API types from the backend schema

## Testing

Run the test suite from the project root:

- `pytest`

## Deployment notes

- Use PostgreSQL in production
- Use a persistent Redis instance for Celery and cached workflows
- Set `CORS_ALLOWED_ORIGINS` to your frontend domain
- Update `VITE_API_BASE_URL` to the deployed backend API URL

## Repository structure

- `apps/` — core backend domains and agents
- `config/` — Django project configuration
- `frontend/` — React user interface
- `infrastructure/` — OCR and storage integrations
- `tests/` — backend test suite

## License

Add the appropriate license here if the project is going to be published.
