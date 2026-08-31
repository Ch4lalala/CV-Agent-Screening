# Evidence-Grounded Recruitment Agent

Phase 1 provides the lightweight application foundation described in the PRD:

- Next.js and TypeScript frontend
- FastAPI backend with `GET /health`
- PostgreSQL database
- Dockerfiles and Docker Compose orchestration

Recruitment features, database models, authentication, and AI/LangGraph workflows are intentionally not part of this phase.

## Prerequisites

- Docker Engine with Docker Compose v2
- Optional for running outside Docker: Node.js 20.9+ and Python 3.12+

## Start with Docker Compose

1. Create the local environment file:

   ```bash
   cp .env.example .env
   ```

2. Replace `POSTGRES_PASSWORD` in `.env` with a strong local value. Do not commit `.env`.

3. Build and start all services:

   ```bash
   docker compose up -d --build
   ```

4. Check service health:

   ```bash
   docker compose ps
   curl http://localhost:8000/health
   ```

   The API response should be:

   ```json
   {"status":"healthy"}
   ```

5. Open the frontend at [http://localhost:3000](http://localhost:3000). FastAPI documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

Stop the stack with:

```bash
docker compose down
```

The PostgreSQL data remains in the `postgres_data` Docker volume. To remove that local development data as well, explicitly run `docker compose down --volumes`.

The Compose file also has local-only defaults, so it can boot without a `.env` file. Creating `.env` and changing the placeholder database password is strongly recommended and required before deployment.

## Run locally without containerizing the application

Start PostgreSQL on the private Compose network:

```bash
docker compose up -d postgres
```

Run the backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

In another terminal, run the frontend:

```bash
cd frontend
npm install
npm run dev
```

## Verification commands

```bash
cd backend && pytest
cd frontend && npm run typecheck && npm run build
docker compose config
```

## Service overview

| Service | Default address | Purpose |
| --- | --- | --- |
| Frontend | `http://localhost:3000` | Next.js application shell |
| Backend | `http://localhost:8000` | FastAPI application API |
| PostgreSQL | `postgres:5432` (Compose network only) | Persistent database service |

Frontend and backend host ports can be changed in `.env`. PostgreSQL is intentionally not published to the host; the backend reaches it at `postgres:5432` on the private Compose network. `NEXT_PUBLIC_API_URL` is embedded into the frontend during the Docker image build and should be the browser-accessible backend URL.
