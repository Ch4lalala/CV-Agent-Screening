"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CandidateTable, type CandidateRow } from "@/components/candidates/candidate-table";
import { CandidateUpload } from "@/components/candidates/candidate-upload";
import { RequirementManager } from "@/components/jobs/requirement-manager";
import { PageHeader } from "@/components/layout/page-header";
import { AnalysisWorkflow } from "@/components/screening/analysis-workflow";
import { Alert } from "@/components/ui/alert";
import { LoadingState } from "@/components/ui/loading-state";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  getCandidateResume,
  getCandidates,
  getErrorMessage,
  getJob,
  getRequirements,
  getScreeningHistory,
  getScreeningProgress,
  screenCandidate,
  updateJob,
} from "@/lib/api/client";
import { candidateDisplayName, formatDate } from "@/lib/format";
import type {
  Candidate,
  CandidateReport,
  Job,
  JobRequirement,
  JobStatus,
  ScreeningRun,
  ScreeningRunStatus,
  ScreeningStage,
} from "@/types/api";

interface ProgressState {
  runId: number | null;
  status: ScreeningRunStatus;
  currentStage: ScreeningStage;
}

function progressFromResponse(response: ScreeningRun | CandidateReport): ProgressState {
  const run = "screening_run" in response ? response.screening_run : response;
  return { runId: run.id, status: run.status, currentStage: run.current_stage };
}

export function JobDetailClient({ jobId }: { jobId: number }) {
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [requirements, setRequirements] = useState<JobRequirement[]>([]);
  const [candidateRows, setCandidateRows] = useState<CandidateRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusSaving, setStatusSaving] = useState(false);
  const [initiatingCandidateId, setInitiatingCandidateId] = useState<number | null>(null);
  const [progressCandidate, setProgressCandidate] = useState<Candidate | null>(null);
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [progressOpen, setProgressOpen] = useState(false);
  const [backgroundNotice, setBackgroundNotice] = useState<string | null>(null);
  const [screeningErrors, setScreeningErrors] = useState<Record<number, string>>({});

  const loadRequirements = useCallback(async () => {
    setRequirements(await getRequirements(jobId));
  }, [jobId]);

  const loadCandidates = useCallback(async () => {
    const candidates = await getCandidates(jobId);
    const rows = await Promise.all(
      candidates.map(async (candidate): Promise<CandidateRow> => {
        const [resume, history] = await Promise.all([
          getCandidateResume(candidate.id).catch(() => null),
          candidate.status === "processing"
            ? getScreeningHistory(candidate.id).catch(() => [])
            : Promise.resolve([]),
        ]);
        return {
          candidate,
          resume,
          activeRun: history.find((run) => run.status === "processing") ?? null,
        };
      }),
    );
    setCandidateRows(rows);
  }, [jobId]);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [jobResponse] = await Promise.all([
        getJob(jobId),
        loadRequirements(),
        loadCandidates(),
      ]);
      setJob(jobResponse);
    } catch (loadError) {
      setError(getErrorMessage(loadError, "Unable to load this vacancy."));
    } finally {
      setLoading(false);
    }
  }, [jobId, loadCandidates, loadRequirements]);

  useEffect(() => {
    void loadPage();
  }, [loadPage]);

  const hasProcessingCandidate = candidateRows.some(
    ({ candidate }) => candidate.status === "processing",
  );

  useEffect(() => {
    if (!hasProcessingCandidate) {
      return;
    }
    const interval = window.setInterval(() => void loadCandidates(), 2000);
    return () => window.clearInterval(interval);
  }, [hasProcessingCandidate, loadCandidates]);

  useEffect(() => {
    if (!progressCandidate || !progress?.runId || progress.status !== "processing") {
      return;
    }
    const candidateId = progressCandidate.id;
    const candidateName = candidateDisplayName(
      progressCandidate.name,
      progressCandidate.original_filename,
    );
    const runId = progress.runId;
    let stopped = false;

    async function poll() {
      try {
        const response = await getScreeningProgress(candidateId, runId);
        if (stopped) {
          return;
        }
        const next = progressFromResponse(response);
        setProgress(next);
        if (next.status !== "processing") {
          await loadCandidates();
          if (!progressOpen) {
            setBackgroundNotice(
              next.status === "completed"
                ? `Screening for ${candidateName} is complete.`
                : "Screening could not be completed. You can retry from the candidate row.",
            );
          }
        }
      } catch {
        // A later poll or page refresh can recover from a transient read failure.
      }
    }

    void poll();
    const interval = window.setInterval(() => void poll(), 1500);
    return () => {
      stopped = true;
      window.clearInterval(interval);
    };
  }, [loadCandidates, progress?.runId, progress?.status, progressCandidate, progressOpen]);

  async function handleStatusChange(status: JobStatus) {
    if (!job || status === job.status) {
      return;
    }
    setStatusSaving(true);
    try {
      setJob(await updateJob(job.id, { status }));
    } catch (statusError) {
      setError(getErrorMessage(statusError, "Unable to update the vacancy status."));
    } finally {
      setStatusSaving(false);
    }
  }

  async function handleScreen(candidate: Candidate) {
    setProgressCandidate(candidate);
    setProgress({ runId: null, status: "processing", currentStage: "queued" });
    setProgressOpen(true);
    setBackgroundNotice(null);
    setInitiatingCandidateId(candidate.id);
    setScreeningErrors((current) => ({ ...current, [candidate.id]: "" }));
    try {
      const started = await screenCandidate(candidate.id);
      setProgress({
        runId: started.screening_run_id,
        status: started.status,
        currentStage: started.current_stage,
      });
      setCandidateRows((current) =>
        current.map((row) =>
          row.candidate.id === candidate.id
            ? {
                ...row,
                candidate: { ...row.candidate, status: "processing" },
              }
            : row,
        ),
      );
    } catch (screenError) {
      setProgressOpen(false);
      setProgress(null);
      setScreeningErrors((current) => ({
        ...current,
        [candidate.id]: getErrorMessage(
          screenError,
          "The screening run could not be started. Try again.",
        ),
      }));
      await loadCandidates().catch(() => undefined);
    } finally {
      setInitiatingCandidateId(null);
    }
  }

  async function handleViewProgress(candidate: Candidate, run: ScreeningRun | null) {
    setProgressCandidate(candidate);
    setBackgroundNotice(null);
    if (run) {
      setProgress({ runId: run.id, status: run.status, currentStage: run.current_stage });
      setProgressOpen(true);
      return;
    }
    try {
      const history = await getScreeningHistory(candidate.id);
      const active = history.find((item) => item.status === "processing") ?? history[0];
      if (active) {
        setProgress({
          runId: active.id,
          status: active.status,
          currentStage: active.current_stage,
        });
        setProgressOpen(true);
      }
    } catch {
      setScreeningErrors((current) => ({
        ...current,
        [candidate.id]: "Unable to load screening progress. Try again.",
      }));
    }
  }

  function closeProgress() {
    setProgressOpen(false);
    if (progress?.status === "processing") {
      setBackgroundNotice("Screening continues in the background.");
    }
  }

  if (loading) {
    return <LoadingState label="Loading vacancy workspace" />;
  }

  if (!job) {
    return (
      <Alert title="Vacancy unavailable">
        <p>{error ?? "This vacancy could not be found."}</p>
        <Link className="text-button" href="/dashboard">Return to vacancies</Link>
      </Alert>
    );
  }

  const progressName = progressCandidate
    ? candidateDisplayName(progressCandidate.name, progressCandidate.original_filename)
    : "candidate";

  return (
    <div className="page-stack">
      {progressOpen && progress ? (
        <AnalysisWorkflow
          candidateName={progressName}
          status={progress.status}
          currentStage={progress.currentStage}
          onClose={closeProgress}
          onViewReport={
            progressCandidate
              ? () => router.push(`/candidates/${progressCandidate.id}`)
              : undefined
          }
          onRetry={
            progressCandidate ? () => void handleScreen(progressCandidate) : undefined
          }
        />
      ) : null}

      <div className="breadcrumbs" aria-label="Breadcrumb">
        <Link href="/dashboard">Vacancies</Link>
        <span aria-hidden="true">/</span>
        <span>{job.title}</span>
      </div>

      <PageHeader
        eyebrow={`Vacancy #${job.id}`}
        title={job.title}
        description={`Created ${formatDate(job.created_at)} · Requirements and evidence remain recruiter-controlled.`}
        actions={
          <div className="header-status-control">
            <StatusBadge status={job.status} />
            <label className="sr-only" htmlFor="job-status">Vacancy status</label>
            <select
              id="job-status"
              aria-label="Vacancy status"
              disabled={statusSaving}
              value={job.status}
              onChange={(event) => void handleStatusChange(event.target.value as JobStatus)}
            >
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        }
      />

      {error ? <Alert>{error}</Alert> : null}
      {backgroundNotice ? (
        <Alert tone="info" title="Background screening">{backgroundNotice}</Alert>
      ) : null}

      <section className="job-brief panel" aria-labelledby="job-brief-title">
        <div className="job-brief-label">
          <span aria-hidden="true">BRIEF</span>
          <p>Job description</p>
        </div>
        <div>
          <h2 id="job-brief-title">Role context</h2>
          <p>{job.description}</p>
        </div>
      </section>

      <RequirementManager
        jobId={job.id}
        requirements={requirements}
        onChanged={loadRequirements}
      />

      <CandidateUpload jobId={job.id} onComplete={loadCandidates} />

      <section className="panel candidate-section" aria-labelledby="candidate-list-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Recruiter review queue</p>
            <h2 id="candidate-list-title">Candidates</h2>
            <p>Screen candidates in the background and review evidence before any human decision.</p>
          </div>
          <span className="section-count">{candidateRows.length} candidates</span>
        </div>
        <CandidateTable
          rows={candidateRows}
          screeningCandidateId={initiatingCandidateId}
          screeningErrors={screeningErrors}
          onScreen={(candidate) => void handleScreen(candidate)}
          onViewProgress={(candidate, run) => void handleViewProgress(candidate, run)}
        />
      </section>
    </div>
  );
}
