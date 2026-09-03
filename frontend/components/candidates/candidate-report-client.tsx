"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CandidateProfileCard } from "@/components/candidates/candidate-profile-card";
import { PageHeader } from "@/components/layout/page-header";
import { AnalysisWorkflow } from "@/components/screening/analysis-workflow";
import { CoverageSummary } from "@/components/screening/coverage-summary";
import { EvidenceMatrix } from "@/components/screening/evidence-matrix";
import { InterviewQuestions } from "@/components/screening/interview-questions";
import { NeedsVerification } from "@/components/screening/needs-verification";
import { ResumeSecurity } from "@/components/screening/resume-security";
import { ScreeningHistory } from "@/components/screening/screening-history";
import { Alert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  ApiError,
  getCandidate,
  getCandidateResume,
  getErrorMessage,
  getJob,
  getLatestScreening,
  getScreeningHistory,
  getScreeningProgress,
  getScreeningRun,
  screenCandidate,
} from "@/lib/api/client";
import { candidateDisplayName, formatDateTime } from "@/lib/format";
import type {
  Candidate,
  CandidateReport,
  Job,
  ResumeMetadata,
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

export function CandidateReportClient({
  candidateId,
  historicalRunId,
}: {
  candidateId: number;
  historicalRunId?: number;
}) {
  const router = useRouter();
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [resume, setResume] = useState<ResumeMetadata | null>(null);
  const [report, setReport] = useState<CandidateReport | null>(null);
  const [history, setHistory] = useState<ScreeningRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [screeningError, setScreeningError] = useState<string | null>(null);
  const [initiating, setInitiating] = useState(false);
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [progressOpen, setProgressOpen] = useState(false);
  const [backgroundNotice, setBackgroundNotice] = useState<string | null>(null);

  const loadPage = useCallback(
    async (showLoading = true) => {
      if (showLoading) {
        setLoading(true);
      }
      setError(null);
      try {
        const candidateResponse = await getCandidate(candidateId);
        const reportRequest = historicalRunId
          ? getScreeningRun(candidateId, historicalRunId)
          : getLatestScreening(candidateId);
        const [jobResponse, resumeResponse, historyResponse, reportResponse] =
          await Promise.all([
            getJob(candidateResponse.job_id),
            getCandidateResume(candidateId).catch((resumeError: unknown) => {
              if (resumeError instanceof ApiError && resumeError.status === 404) {
                return null;
              }
              throw resumeError;
            }),
            getScreeningHistory(candidateId),
            reportRequest.catch((reportError: unknown) => {
              if (reportError instanceof ApiError && reportError.status === 404) {
                return null;
              }
              throw reportError;
            }),
          ]);
        setCandidate(candidateResponse);
        setJob(jobResponse);
        setResume(resumeResponse);
        setHistory(historyResponse);
        setReport(reportResponse);
      } catch (loadError) {
        setError(getErrorMessage(loadError, "Unable to load this candidate report."));
      } finally {
        setLoading(false);
      }
    },
    [candidateId, historicalRunId],
  );

  useEffect(() => {
    void loadPage();
  }, [loadPage]);

  useEffect(() => {
    if (candidate?.status !== "processing") {
      return;
    }
    const interval = window.setInterval(() => void loadPage(false), 2000);
    return () => window.clearInterval(interval);
  }, [candidate?.status, loadPage]);

  useEffect(() => {
    if (!progress?.runId || progress.status !== "processing") {
      return;
    }
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
          await loadPage(false);
          if (!progressOpen) {
            setBackgroundNotice(
              next.status === "completed"
                ? "Screening is complete. The candidate report is ready."
                : "Screening could not be completed. You can retry when ready.",
            );
          }
        }
      } catch {
        // Polling is retried; persisted state allows recovery after refresh.
      }
    }

    void poll();
    const interval = window.setInterval(() => void poll(), 1500);
    return () => {
      stopped = true;
      window.clearInterval(interval);
    };
  }, [candidateId, loadPage, progress?.runId, progress?.status, progressOpen]);

  async function handleScreen() {
    if (!candidate) {
      return;
    }
    setInitiating(true);
    setScreeningError(null);
    setBackgroundNotice(null);
    setProgress({ runId: null, status: "processing", currentStage: "queued" });
    setProgressOpen(true);
    try {
      const started = await screenCandidate(candidate.id);
      setProgress({
        runId: started.screening_run_id,
        status: started.status,
        currentStage: started.current_stage,
      });
      setCandidate({ ...candidate, status: "processing" });
      if (historicalRunId) {
        router.push(`/candidates/${candidate.id}`);
      }
    } catch (screenError) {
      setProgressOpen(false);
      setProgress(null);
      setScreeningError(
        getErrorMessage(
          screenError,
          "The screening run could not be started. You can retry.",
        ),
      );
      await loadPage(false);
    } finally {
      setInitiating(false);
    }
  }

  function openLatestProgress() {
    const active = history.find((run) => run.status === "processing") ?? history[0];
    if (!active) {
      return;
    }
    setProgress({
      runId: active.id,
      status: active.status,
      currentStage: active.current_stage,
    });
    setBackgroundNotice(null);
    setProgressOpen(true);
  }

  function closeProgress() {
    setProgressOpen(false);
    if (progress?.status === "processing") {
      setBackgroundNotice("Screening continues in the background.");
    }
  }

  async function viewCompletedReport() {
    setProgressOpen(false);
    if (historicalRunId) {
      router.push(`/candidates/${candidateId}`);
      return;
    }
    await loadPage(false);
  }

  if (loading) {
    return <LoadingState label="Loading candidate evidence" />;
  }

  if (!candidate || !job) {
    return (
      <Alert title="Candidate unavailable">
        <p>{error ?? "This candidate could not be found."}</p>
        <Link className="text-button" href="/dashboard">Return to vacancies</Link>
      </Alert>
    );
  }

  const candidateName = candidateDisplayName(candidate.name, candidate.original_filename);
  const latestAttempt = history[0];
  const showingOlderCompletedRun =
    report !== null && latestAttempt !== undefined && latestAttempt.id !== report.screening_run.id;
  const resumeReady = resume?.extraction_status === "completed";
  const processing = candidate.status === "processing";

  return (
    <div className="page-stack report-page">
      {progressOpen && progress ? (
        <AnalysisWorkflow
          candidateName={candidateName}
          status={progress.status}
          currentStage={progress.currentStage}
          onClose={closeProgress}
          onViewReport={() => void viewCompletedReport()}
          onRetry={() => void handleScreen()}
        />
      ) : null}

      <div className="breadcrumbs" aria-label="Breadcrumb">
        <Link href="/dashboard">Vacancies</Link>
        <span aria-hidden="true">/</span>
        <Link href={`/jobs/${candidate.job_id}`}>{job.title}</Link>
        <span aria-hidden="true">/</span>
        <span>{candidateName}</span>
      </div>

      {historicalRunId && report ? (
        <Alert tone="info" title="Viewing historical screening">
          <p>
            Run #{report.screening_run.id} · {formatDateTime(report.screening_run.started_at)}.
            This preserved snapshot may not reflect later screenings or requirement changes.
          </p>
          <Link className="text-button" href={`/candidates/${candidate.id}`}>
            View latest completed report
          </Link>
        </Alert>
      ) : null}

      {showingOlderCompletedRun && !historicalRunId ? (
        <Alert tone={latestAttempt?.status === "processing" ? "info" : "warning"} title={latestAttempt?.status === "processing" ? "A new screening is in progress" : "Latest screening attempt did not complete"}>
          <p>The most recent completed report remains visible until a new run completes.</p>
        </Alert>
      ) : null}

      {backgroundNotice ? (
        <Alert tone="info" title="Background screening">{backgroundNotice}</Alert>
      ) : null}

      <PageHeader
        eyebrow="Candidate evidence report"
        title={candidateName}
        description={job.title}
        actions={
          <div className="report-header-actions">
            <StatusBadge status={candidate.status} />
            <button
              className="button button-primary"
              type="button"
              disabled={initiating || !resumeReady}
              onClick={processing ? openLatestProgress : () => void handleScreen()}
            >
              {initiating
                ? "Starting…"
                : processing
                  ? "View progress"
                  : candidate.status === "uploaded"
                    ? "Screen candidate"
                    : "Run screening again"}
            </button>
          </div>
        }
      />

      <section className="candidate-summary-bar" aria-label="Candidate summary">
        <div>
          <span>Resume</span>
          <strong>{resume?.original_filename ?? candidate.original_filename ?? "No PDF attached"}</strong>
        </div>
        <div>
          <span>Extraction</span>
          <strong>{resume ? `${resume.page_count} pages · ${resume.extraction_status}` : "Unavailable"}</strong>
        </div>
        <div>
          <span>Latest completed screening</span>
          <strong>{report ? formatDateTime(report.screening_run.finished_at) : "Not screened"}</strong>
        </div>
        <div>
          <span>Model</span>
          <strong>{report?.screening_run.model_name ?? latestAttempt?.model_name ?? "Not recorded"}</strong>
        </div>
      </section>

      {error ? <Alert title="Report unavailable">{error}</Alert> : null}
      {screeningError ? (
        <Alert title="Unable to start screening">
          <p>{screeningError}</p>
          <button className="text-button" type="button" onClick={() => void handleScreen()}>
            Retry screening
          </button>
        </Alert>
      ) : null}

      {processing ? (
        <Alert tone="info" title="Candidate screening is in progress">
          <p>The backend continues processing if you leave or refresh this page.</p>
          <button className="text-button" type="button" onClick={openLatestProgress}>
            View progress
          </button>
        </Alert>
      ) : null}

      {!resumeReady && resume ? (
        <Alert tone="warning" title="Resume is not ready for screening">
          {resume.message ?? "Upload a text-based PDF before starting analysis."}
        </Alert>
      ) : null}

      {!report ? (
        <EmptyState
          icon="◎"
          title={candidate.status === "failed" ? "Screening failed" : processing ? "Screening in progress" : "No completed screening yet"}
          description={
            candidate.status === "failed"
              ? "ProofHire could not complete this analysis. Retry when ready."
              : processing
                ? "You can leave this page while the evidence workflow continues."
                : "Start screening to create an evidence-grounded report for recruiter review."
          }
          action={
            <button
              className="button button-primary"
              type="button"
              disabled={initiating || !resumeReady}
              onClick={processing ? openLatestProgress : () => void handleScreen()}
            >
              {processing ? "View progress" : candidate.status === "failed" ? "Retry screening" : "Screen candidate"}
            </button>
          }
        />
      ) : (
        <>
          <ResumeSecurity security={report.security} />
          <CoverageSummary
            required={report.coverage.required}
            preferred={report.coverage.preferred}
          />
          <EvidenceMatrix results={report.evidence_results} />
          <NeedsVerification
            names={report.needs_verification}
            results={report.evidence_results}
          />
          <div className="report-secondary-grid">
            <InterviewQuestions questions={report.interview_questions} />
            <CandidateProfileCard profile={report.candidate_profile} />
          </div>
        </>
      )}

      <ScreeningHistory
        candidateId={candidate.id}
        runs={history}
        viewedRunId={report?.screening_run.id}
      />

      <div className="human-control-note">
        <span aria-hidden="true">✓</span>
        <p>
          <strong>Recruiter decision remains human.</strong>
          This report presents evidence and uncertainty. It does not hire, reject, or rank candidates.
        </p>
      </div>
    </div>
  );
}
