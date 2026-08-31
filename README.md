# Evidence-Grounded Recruitment Agent

Phase 2 provides the lightweight application and persistence foundation described in the PRD:

- Next.js and TypeScript frontend
- FastAPI backend with `GET /health`
- PostgreSQL database
- SQLAlchemy 2.x models and Alembic migrations
- REST CRUD APIs for jobs, job requirements, and candidate metadata
- Dockerfiles and Docker Compose orchestration

Authentication, CV/PDF upload, screening, and AI/LangGraph workflows are intentionally not part of this phase.

## Prerequisites

- Docker Engine with Docker Compose v2
- Optional for running outside Docker: Node.js 20.9+ and Python 3.12+

## Start with Docker Compose

1. Create the local environment file:

   ```bash
   cp .env.example .env
   ```

2. Replace `POSTGRES_PASSWORD` in `.env` with a strong local value. Do not commit `.env`. The `DEVELOPMENT_USER_*` values identify the temporary recruiter used until authentication is implemented.

3. Build and start all services. The backend applies pending Alembic migrations before starting FastAPI:

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

Verify or manually apply the current migration inside Docker with:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

Stop the stack with:

```bash
docker compose down
```

The PostgreSQL data remains in the `postgres_data` Docker volume. To remove that local development data as well, explicitly run `docker compose down --volumes`.

The Compose file also has local-only defaults, so it can boot without a `.env` file. Creating `.env` and changing the placeholder database password is strongly recommended and required before deployment.

## Development user

Authentication is deliberately deferred. In `APP_ENV=development`, startup creates one development user from:

- `DEVELOPMENT_USER_EMAIL`
- `DEVELOPMENT_USER_FULL_NAME`

All Phase 2 endpoints resolve ownership through one temporary dependency in `backend/app/services/development_user.py`. The user has a non-authenticating password marker, no credentials are accepted by the API, and `password_hash` is never included in responses. This dependency is intended to be replaced by real authentication later.

The development seed is disabled when `APP_ENV` is not `development`.

## Phase 2 API

All resource endpoints use the `/api/v1` prefix.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/jobs` | Create a job for the development user |
| `GET` | `/api/v1/jobs` | List the user's jobs |
| `GET` | `/api/v1/jobs/{job_id}` | Get a job |
| `PATCH` | `/api/v1/jobs/{job_id}` | Update a job |
| `DELETE` | `/api/v1/jobs/{job_id}` | Delete a job and its child records |
| `POST` | `/api/v1/jobs/{job_id}/requirements` | Create a requirement |
| `GET` | `/api/v1/jobs/{job_id}/requirements` | List a job's requirements |
| `PATCH` | `/api/v1/jobs/{job_id}/requirements/{requirement_id}` | Update a requirement |
| `DELETE` | `/api/v1/jobs/{job_id}/requirements/{requirement_id}` | Delete a requirement |
| `POST` | `/api/v1/jobs/{job_id}/candidates` | Create candidate metadata |
| `GET` | `/api/v1/jobs/{job_id}/candidates` | List a job's candidates |
| `GET` | `/api/v1/candidates/{candidate_id}` | Get candidate metadata |
| `PATCH` | `/api/v1/candidates/{candidate_id}` | Update candidate metadata |
| `DELETE` | `/api/v1/candidates/{candidate_id}` | Delete candidate metadata |

Candidate creation does not accept files or paths. `original_filename` and `resume_path` remain `null` until the upload phase.

Example job creation:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{"title":"Backend Engineer Intern","description":"Build reliable APIs."}'
```

## Database schema

The initial Alembic migration creates:

- `users`
- `jobs`
- `job_requirements`
- `candidates`

Jobs belong to users. Requirements and candidates belong to jobs. Foreign keys use database-level cascading from parent to child; deleting a job cannot delete its user.

Allowed values are enforced in both Pydantic and the database:

- Job status: `draft`, `active`, `closed`
- Requirement type: `required`, `preferred`
- Candidate status: `uploaded`, `processing`, `completed`, `failed`

## Run tests locally

Backend tests use a fresh in-memory SQLite database for every test and enable foreign-key enforcement. They do not use or modify the development PostgreSQL database.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Verification commands

```bash
docker compose config --quiet
docker compose up -d --build
docker compose exec backend alembic current
docker compose exec backend alembic check

cd backend
.venv/bin/pytest

cd ../frontend
npm run typecheck
npm run build
```

## Service overview

| Service | Default address | Purpose |
| --- | --- | --- |
| Frontend | `http://localhost:3000` | Next.js application shell |
| Backend | `http://localhost:8000` | FastAPI application API |
| PostgreSQL | `postgres:5432` (Compose network only) | Persistent database service |

Frontend and backend host ports can be changed in `.env`. PostgreSQL is intentionally not published to the host; the backend reaches it at `postgres:5432` on the private Compose network. `NEXT_PUBLIC_API_URL` is embedded into the frontend during the Docker image build and should be the browser-accessible backend URL.
