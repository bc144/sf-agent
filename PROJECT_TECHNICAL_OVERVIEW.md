# Agent IA Oracle – Technical Overview

## Repository Layout
- `demo/` – Python workspace containing the FastAPI service, vector-search ingestion scripts, a CLI assistant, and a Streamlit dashboard.
- `front/Archive (1)/` – React + TypeScript single-page application serving as the primary web client.
- `.venv/` – Local Python virtual environment (not tracked in Git).

## Backend Service (`demo/api`)
- **Framework & Runtime:** FastAPI with Uvicorn, packaged via `Makefile` targets for setup and launch.
- **Core Dependencies:** `sentence-transformers` for embeddings, `qdrant-client` for vector storage, `openai` for conversational intent parsing, `pydantic` for schema validation, and `python-dotenv` for configuration loading.
- **Endpoints:**
  - `GET /` and `GET /health` expose liveness details.
  - `POST /search` encodes the free-text query with `all-MiniLM-L6-v2`, applies structured filters, and searches Qdrant using a named vector (`text`) with cosine similarity. Each hit is normalized into a `ProductCard` enriched with a deterministic "why" explanation derived from constraints.
  - `POST /ask` delegates query interpretation to an OpenAI model under a guardrailed system prompt, converts its structured response into `Constraints`, reuses the vector search path, and returns both conversational text and ranked items with fallbacks for robustness.
- **Support Modules:**
  - `models.py` defines Pydantic schemas for requests/responses.
  - `qdrant_setup.py` ensures the `products` collection exists, configures the 384-dim cosine vector space, and adds payload indexes for filterable fields.
  - `oracle_loader.py` selects the product catalog source from OCI Object Storage, S3-compatible storage, a pre-signed Oracle PAR link, or a bundled CSV, normalizing all inputs via Pandas.
  - `ingest_csv.py` runs the end-to-end ingestion pipeline: normalizes tabular data, builds natural-language documents, generates embeddings, and upserts points to Qdrant in 100-item batches.
  - `agent_cli.py` wraps the API with `pydantic_ai` to offer a terminal-based assistant that always issues API-backed product lookups and renders tabular results with Rich.

## Streamlit Dashboard (`demo/ui`)
- Provides an alternative operator-facing interface for the search endpoint.
- Loads filter options from the local CSV, lets users set structured constraints, and renders product cards with optional images and rationale text.
- Uses `requests` to call the FastAPI backend through the same payloads as public consumers.

## Shared Types (`demo/api-types.ts`)
- Supplies TypeScript interfaces and helper utilities mirroring the FastAPI schemas, plus a reference API client and React hook blueprint for consumer applications.

## Frontend SPA (`front/Archive (1)`)
- **Stack:** React 19, Vite 7, TypeScript 5.9, Tailwind CSS v4 (via the Vite plugin), Framer Motion for transitions, and Lucide icons.
- **App Flow:**
  - `App.tsx` mounts a single route rendering `ProductSearch`.
  - `ProductSearch.tsx` drives both direct search and conversational queries, exposing filters, an optional notes field, result count control, and animated presentation of results.
  - Integrates with the backend via `fetch` calls to `POST /search` and `POST /ask`, updates local state with returned items, and displays availability metadata (`colors`, `sizes`) along with the backend-generated rationale.
- **Tooling:** ESLint flat config with React hooks rules, Tailwind imported through the new `@tailwindcss/vite` plugin, and standard Vite build commands (`npm run dev|build|preview`).

## Configuration & Operations
- **Environment Variables** (stored in `demo/.env`; values omitted for safety):
  - `QDRANT_URL`, `QDRANT_CLIENT` – remote vector database endpoint and API key.
  - `OPENAI_API_KEY` – key for chat-completions used by the conversational agent.
  - `ORACLE_OCI`, `NAMESPACE`, `BUCKET`, `OBJECT` – flips and identifiers for OCI-based dataset sourcing.
  - Optional S3-compatible variables (`ORACLE_S3`, `ORACLE_S3_ENDPOINT`, `ORACLE_S3_KEY`, `ORACLE_S3_SECRET`, `ORACLE_S3_BUCKET`, `ORACLE_S3_KEYNAME`).
- **Setup Workflow:**
  - `make api-venv && make api` to provision the FastAPI server (default port 8000).
  - `make qdrant-setup` followed by `make ingest` to initialize and populate the Qdrant collection.
  - `make agent` to launch the CLI assistant, or `make ui` for the Streamlit dashboard.
- **Frontend Commands:** `npm install` inside `front/Archive (1)` and use the Vite scripts to develop or build the SPA; outputs land in `dist/` for static hosting.
- **Testing:** No automated tests or lint workflows are currently defined for the backend; the frontend relies on manual use of ESLint via `npm run lint`.

## Objective Pitch
This repository packages a functioning product-discovery stack that blends deterministic search filters with vector similarity and a guarded conversational layer. Teams can ingest thousands of catalog items into Qdrant with one script, serve consistent recommendations through FastAPI, and surface the experience either via the pre-built React client or the Streamlit console. The design keeps control over data residency (OCI, S3, or local CSV) and exposes predictable interfaces, enabling rapid validation of semantic search workflows without bespoke infrastructure.
