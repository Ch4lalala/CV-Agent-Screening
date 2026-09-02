# Evidence-Grounded Recruitment Agent

Phase 7.5 provides the lightweight application, secure document ingestion, evidence-grounded recruitment graph, persistent candidate reports, and recruiter-facing workflow described in the PRD:

- Responsive Next.js and TypeScript recruiter workspace
- FastAPI backend with `GET /health`
- PostgreSQL database
- SQLAlchemy 2.x models and Alembic migrations
- REST CRUD APIs for jobs, job requirements, and candidate metadata
- Temporary PDF, DOCX, and TXT job-document import with AI-generated vacancy drafts
- AI-generated qualification drafts from manually written job descriptions
- Deterministic atomic-requirement validation, conservative deduplication, and recruiter warnings
- Secure PDF upload with UUID filenames and PyMuPDF text extraction
- Persistent resume metadata and Docker-managed file storage
- Lazy, provider-agnostic AI client for OpenAI-compatible endpoints
- Pydantic-validated structured AI output with a bounded fallback
- In-process asynchronous LangGraph workflow with persisted stage progress and historical screening runs
- Deterministic evidence-quote verification, uncertainty grouping, and coverage
- Normalized candidate profiles, evidence, citations, and interview questions
- Latest-report, run-history, and specific-run APIs
- Dashboard, job setup, requirement management, PDF upload, and candidate workflow
- Evidence-first candidate reports with coverage, citations, verification flags, interview questions, profile context, and screening history
- Dockerfiles and Docker Compose orchestration

Authentication, Phase 8 prompt-injection detection, resume privacy filtering, GitHub verification, and autonomous hiring decisions are intentionally not part of this phase. Job-document prompts defensively treat source content as untrusted data, but this is not presented as prompt-injection detection. The UI never presents an overall candidate score or hiring recommendation; recruiters remain responsible for interpreting the evidence.

## Prerequisites

- Docker Engine with Docker Compose v2
- Optional for running outside Docker: Node.js 20.9+ and Python 3.12+

## Start with Docker Compose

1. Create the local environment file:

   ```bash
   cp .env.example .env
   ```

2. Replace `POSTGRES_PASSWORD` in `.env` with a strong local value. Do not commit `.env`. The `DEVELOPMENT_USER_*` values identify the temporary recruiter used until authentication is implemented. `MAX_CV_SIZE_MB` and `MAX_JOB_DOCUMENT_SIZE_MB` both default to `5`. `CORS_ORIGINS` is a comma-separated allowlist for browser origins and defaults to the local frontend. AI values may remain empty when working on non-AI features.

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

The recruiter workflow starts at `/dashboard`: write a job description manually or import one from a document, review the generated required/preferred criteria, confirm the vacancy, upload one or more PDF resumes, and screen a ready candidate. Starting a screening returns `202 Accepted` quickly and the in-process background task persists each real LangGraph stage. The UI polls that persisted state every 1.5 seconds while a progress modal is open. The modal can be dismissed without cancelling the run, and **View progress** restores it after navigation or refresh. Missing AI configuration and provider failures are shown as recoverable errors; manually entered data and uploaded candidates remain available.

Verify or manually apply the current migration inside Docker with:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

Stop the stack with:

```bash
docker compose down
```

PostgreSQL data remains in `postgres_data`, and uploaded PDFs remain in `resume_data`. To remove both local development volumes explicitly, run `docker compose down --volumes`.

The Compose file also has local-only defaults, so it can boot without a `.env` file. Creating `.env` and changing the placeholder database password is strongly recommended and required before deployment.

## Development user

Authentication is deliberately deferred. In `APP_ENV=development`, startup creates one development user from:

- `DEVELOPMENT_USER_EMAIL`
- `DEVELOPMENT_USER_FULL_NAME`

All resource endpoints resolve ownership through one temporary dependency in `backend/app/services/development_user.py`. The user has a non-authenticating password marker, no credentials are accepted by the API, and `password_hash` is never included in responses. This dependency is intended to be replaced by real authentication later.

The development seed is disabled when `APP_ENV` is not `development`.

## Frontend development

For a frontend process running outside Docker, configure the browser-visible backend URL and start Next.js:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

The default `frontend/.env.example` points to `http://localhost:8000`. `NEXT_PUBLIC_API_URL` is the only frontend API setting and must be reachable by the browser. Browser requests are centralized in `frontend/lib/api/client.ts`; secrets and server-only provider settings must never use the `NEXT_PUBLIC_` prefix.

The principal routes are:

- `/dashboard` — job overview and aggregate candidate status
- `/jobs/new` — create a job
- `/jobs/{jobId}` — edit job status, manage requirements, upload PDFs, and screen candidates
- `/candidates/{candidateId}` — latest evidence report and screening history
- `/candidates/{candidateId}/screenings/{runId}` — immutable historical report

The report clearly separates required and preferred coverage and shows text labels for `supported`, `partial`, and `no evidence`. Evidence quotations retain their source and page when available, uncertain items are collected under “Needs verification,” and generated interview questions can be copied but are never sent automatically. Candidate profile data is secondary context rather than proof of a requirement.

## Manual vacancy criteria draft

On `/jobs/new`, **Write manually** accepts a recruiter-authored title and job description. **Create & review criteria** sends those details to `POST /api/v1/jobs/analyze-description`, which uses the same structured job-analysis service as document import. This analysis endpoint does not persist a Job or JobRequirement.

The shared analysis prompt recognizes required/preferred headings and sentence-level signals, requests independently verifiable criteria, and preserves alternatives such as “Go or a comparable programming language” without silently making Go mandatory. The recruiter-entered title and description remain authoritative. The returned requirements are editable drafts: the recruiter can edit, remove, add, and reclassify them before confirmation.

Only **Confirm & create vacancy** persists the Job and final JobRequirement rows. If AI analysis is unavailable, the same review screen opens with an empty criteria list and a safe message so requirements can still be entered manually. Candidate screening remains a separate explicit action.

## Job-document import

On `/jobs/new`, choose **Upload job document** to submit a PDF, DOCX, or TXT file up to `MAX_JOB_DOCUMENT_SIZE_MB` (5 MB by default). Image-only PDFs, OCR, spreadsheets, presentations, and images are not supported. The backend validates the extension, MIME type, file signature where practical, and size before extracting text.

The source document is written under an operating-system temporary directory using a UUID filename. It is deleted after the AI response or any failure and is never stored in PostgreSQL or the resume volume. Extracted job text is sent to the configured external AI provider for one structured draft call; one bounded retry is allowed for invalid or obviously composite output.

The import endpoint returns only an editable draft. It does not create a Job:

```bash
curl -X POST http://localhost:8000/api/v1/jobs/import \
  -F 'file=@./vacancy.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document'
```

The backend requests one independently verifiable qualification per requirement. A deterministic pass splits only obvious lists of known technologies, normalizes conservative aliases such as Postgres/PostgreSQL, consolidates duplicates, excludes vague or personal criteria, and flags ambiguous composites rather than guessing. Warnings are advisory and do not make legal conclusions.

The frontend requires recruiter review of the generated title, description, requirement names, descriptions, and required/preferred types. Only **Confirm & create vacancy** invokes the existing Job and JobRequirement CRUD APIs. Once saved, imported requirements are ordinary recruiter-authoritative requirements and use the same candidate screening path as manually created jobs. Import never starts screening automatically.

## Optional AI provider configuration

All model access is centralized in `backend/app/ai`. The integration uses LangChain's `ChatOpenAI` adapter and expects an OpenAI-compatible chat endpoint. Future services should use `AIClient` rather than construct provider clients directly.

Configure the provider in `.env` only when an AI call is needed:

```env
AI_API_KEY=replace-with-provider-api-key
AI_BASE_URL=https://provider.example/v1
AI_MODEL=replace-with-model-id
AI_TIMEOUT_SECONDS=60
AI_MAX_RETRIES=2
AI_TEMPERATURE=0
```

- `AI_API_KEY` and `AI_MODEL` are required only for AI calls.
- `AI_BASE_URL` is optional; leave it empty to use the adapter's default OpenAI endpoint.
- `AI_TIMEOUT_SECONDS` limits each provider attempt and defaults to `60`.
- `AI_MAX_RETRIES` controls the adapter's bounded retry count and defaults to `2`.
- `AI_TEMPERATURE` defaults to `0` for deterministic structured responses.

The backend, database APIs, PDF ingestion, and `GET /health` start and work without AI credentials. This allows the development provider to be replaced later by the organizer model through environment changes only.

The explicit connectivity endpoint makes one small model request and validates it with the internal `AIHealthResponse` Pydantic schema:

```bash
curl -X POST http://localhost:8000/api/v1/ai/test
```

A successful response includes `status`, `model`, and a short `message`. Missing `AI_API_KEY` or `AI_MODEL` returns a clear `503` without affecting other endpoints. Provider and parsing failures return sanitized errors; API keys, prompts, and raw model responses are not logged or returned.

Structured calls prefer native function calling. If an adapter does not implement it, or an OpenAI-compatible endpoint reports the native request shape as unsupported, the client makes one plain JSON request and validates that response with the same Pydantic schema. There are no repair loops.

## Core recruitment graph

LangGraph runs inside the FastAPI backend; it is not a separate service. The Phase 5 graph executes:

```text
normalize_requirements
  -> extract_candidate_profile
  -> match_evidence
  -> analyze_uncertainty
  -> generate_interview_questions
  -> generate_report
```

The normal provider path has four batched model operations: one each for requirement normalization, candidate extraction, all requirement evidence, and targeted interview questions. The interview operation is skipped when there are no uncertainties, and evidence analysis is skipped when no requirements were produced. As documented above, an operation may make one compatibility fallback call if the provider rejects native structured output.

Recruiter-defined requirements remain authoritative. The response keeps the original recruiter name and description alongside any conservative normalization, and AI-derived requirements are accepted only when the job has no manual requirements.

Evidence quotes are retained only when an exact equivalent exists in the extracted resume after conservative Unicode, whitespace, and case normalization with word boundaries. Unsupported quotes are discarded and the assessment is downgraded. Candidate-provided GitHub and portfolio URLs are retained only when they occur in the resume; they are not visited or verified.

The graph treats resume content as untrusted data and explicitly instructs the model not to follow document instructions. Phase 5 does not claim prompt-injection detection; that remains a later phase.

Run and persist a screening with:

```bash
curl -X POST http://localhost:8000/api/v1/candidates/1/screen
```

The endpoint requires a successfully extracted resume and configured AI provider. It creates the run, marks the candidate as `processing`, schedules the graph in the FastAPI process, and returns `202 Accepted` with the new run ID:

```json
{
  "screening_run_id": 12,
  "candidate_id": 1,
  "status": "processing",
  "current_stage": "queued"
}
```

Poll the persisted run while it is processing:

```bash
curl http://localhost:8000/api/v1/candidates/1/screenings/12
```

Processing and failed runs return run metadata, including `current_stage` and `current_stage_updated_at`. A completed run returns the immutable evidence report with transparent required/preferred coverage, individual evidence assessments, uncertainty, and up to five targeted questions. It never returns a hiring recommendation or black-box match score.

Screening sends the job data and extracted resume text to the configured external AI provider. The background task uses a separate database session and commits progress only after actual LangGraph node updates; it does not use fake percentages or timers. After the graph finishes, a short transaction persists the immutable report snapshot and normalized rows. Missing inputs return `404`, and an incomplete extraction or concurrent run returns `409`. Provider and graph failures are persisted as a sanitized failed run so the recruiter can retry.

Persisted stages follow the graph without exposing internal labels in the UI:

```text
queued
  -> normalize_requirements
  -> extract_candidate_profile
  -> match_evidence
  -> analyze_uncertainty
  -> generate_interview_questions
  -> generate_report
  -> completed | failed
```

Candidate screening status follows:

```text
uploaded -> processing -> completed
                  \----> failed
completed/failed -> processing (on a later screening)
```

Only one `processing` run is allowed per candidate. PostgreSQL enforces this with a partial unique index, while candidate row locking and application checks provide a clear `409` response. The potentially slow graph/provider call runs without a database transaction held open.

Completed runs are historical snapshots. Later screenings or requirement edits create or affect new state without rewriting old `report_json`, profile, evidence, citations, or questions. Failed runs retain only a sanitized error message.

## Application API

All resource endpoints use the `/api/v1` prefix.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/jobs` | Create a job for the development user |
| `POST` | `/api/v1/jobs/analyze-description` | Generate an editable criteria draft from manual vacancy text without persistence |
| `POST` | `/api/v1/jobs/import` | Extract a temporary job document and return an editable AI draft without persistence |
| `GET` | `/api/v1/jobs` | List the user's jobs |
| `GET` | `/api/v1/jobs/{job_id}` | Get a job |
| `PATCH` | `/api/v1/jobs/{job_id}` | Update a job |
| `DELETE` | `/api/v1/jobs/{job_id}` | Delete a job and its child records |
| `POST` | `/api/v1/jobs/{job_id}/requirements` | Create a requirement |
| `GET` | `/api/v1/jobs/{job_id}/requirements` | List a job's requirements |
| `PATCH` | `/api/v1/jobs/{job_id}/requirements/{requirement_id}` | Update a requirement |
| `DELETE` | `/api/v1/jobs/{job_id}/requirements/{requirement_id}` | Delete a requirement |
| `POST` | `/api/v1/jobs/{job_id}/candidates` | Upload a PDF and create candidate/resume metadata |
| `GET` | `/api/v1/jobs/{job_id}/candidates` | List a job's candidates |
| `GET` | `/api/v1/candidates/{candidate_id}` | Get candidate metadata |
| `GET` | `/api/v1/candidates/{candidate_id}/resume` | Get extraction metadata without resume text |
| `PATCH` | `/api/v1/candidates/{candidate_id}` | Update candidate metadata |
| `DELETE` | `/api/v1/candidates/{candidate_id}` | Delete candidate, resume, file, and screening data |
| `POST` | `/api/v1/candidates/{candidate_id}/screen` | Create a screening run and return `202 Accepted` |
| `GET` | `/api/v1/candidates/{candidate_id}/screening` | Get the latest completed screening report |
| `GET` | `/api/v1/candidates/{candidate_id}/screenings` | List screening-run summaries newest first |
| `GET` | `/api/v1/candidates/{candidate_id}/screenings/{run_id}` | Poll run metadata or get its completed historical report |
| `POST` | `/api/v1/ai/test` | Explicitly test optional AI configuration and structured output |

The candidate endpoint uses `multipart/form-data` for Phase 3 uploads. The existing Phase 2 JSON metadata request remains supported for backward compatibility, but multipart PDF upload is the primary contract.

Example job creation:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{"title":"Backend Engineer Intern","description":"Build reliable APIs."}'
```

Example PDF upload with optional candidate metadata:

```bash
curl -X POST http://localhost:8000/api/v1/jobs/1/candidates \
  -F 'file=@./candidate.pdf;type=application/pdf' \
  -F 'name=Synthetic Candidate' \
  -F 'email=candidate@example.com'
```

Only PDF files are supported. The backend checks the `.pdf` extension, `application/pdf` MIME type, `%PDF-` signature, and the configured maximum size. OCR is not performed; image-only or empty PDFs are stored with an extraction status of `failed` and a clear message.

The upload response and resume metadata endpoint return page count, extraction status, and extracted-text length. They do not return extracted resume text or the internal storage path.

## Resume storage

- `CV_STORAGE_PATH` defaults to `/app/storage/resumes` in Docker.
- `MAX_CV_SIZE_MB` defaults to `5`.
- The backend stores files as UUID-based `.pdf` names rather than using client filenames.
- Original filenames are reduced to safe basenames before persistence.
- The `resume_data` named volume keeps files outside ephemeral container layers and public frontend directories.
- Candidate or parent-job deletion removes resume rows and safely removes files only when their resolved paths are inside the configured storage directory.
- If the file is already missing, candidate deletion still succeeds.

Candidate status starts as `uploaded` after successful ingestion. `resume_documents.extraction_status` separately records `pending`, `completed`, or `failed`; candidate status changes only when screening begins.

## Database schema

The Alembic migrations create:

- `users`
- `jobs`
- `job_requirements`
- `candidates`
- `resume_documents`
- `screening_runs`
- `candidate_profiles`
- `evidence_results`
- `evidence_items`
- `interview_questions`

Jobs belong to users. Requirements and candidates belong to jobs. Each candidate has at most one current resume document and may have multiple screening runs. Each run owns one profile plus its evidence, citations, and interview questions. Foreign keys cascade screening data when a candidate is deleted; the resume file deletion flow remains in place. Deleting child screening records cannot delete their candidate, job, or user. Evidence links to recruiter requirements use `ON DELETE SET NULL`, preserving the historical requirement name and type if a requirement is later removed.

Allowed values are enforced in both Pydantic and the database:

- Job status: `draft`, `active`, `closed`
- Requirement type: `required`, `preferred`
- Candidate status: `uploaded`, `processing`, `completed`, `failed`
- Resume extraction status: `pending`, `completed`, `failed`
- Screening run status: `pending`, `processing`, `completed`, `failed`
- Screening stage: `queued`, six graph-node stages, `completed`, `failed`
- Evidence status: `supported`, `partial`, `no_evidence`
- Evidence confidence: `high`, `medium`, `low`

## Run tests locally

Backend tests use a fresh in-memory SQLite database and temporary resume directory for every test. Generated PDFs exercise validation, extraction, persistence, collision prevention, transaction cleanup, and safe deletion without relying on manually created files.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Frontend interaction tests cover manual AI pre-population, recruiter edits, deletion, type changes, additions, confirmation, graceful AI fallback, upload, persisted screening progress, dismissal, completion/failure actions, and processing-row recovery:

```bash
cd frontend
npm ci
npm test
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
npm test
npm run typecheck
npm run build
```

## Service overview

| Service | Default address | Purpose |
| --- | --- | --- |
| Frontend | `http://localhost:3000` | Next.js recruiter workspace |
| Backend | `http://localhost:8000` | FastAPI application API |
| PostgreSQL | `postgres:5432` (Compose network only) | Persistent database service |

The backend's `/app/storage/resumes` directory is backed by the `resume_data` Docker volume.

Frontend and backend host ports can be changed in `.env`. PostgreSQL is intentionally not published to the host; the backend reaches it at `postgres:5432` on the private Compose network. `NEXT_PUBLIC_API_URL` is embedded into the frontend during the Docker image build and should be the browser-accessible backend URL. When the frontend origin changes, add that exact origin to the comma-separated `CORS_ORIGINS` value and rebuild/restart the backend.
