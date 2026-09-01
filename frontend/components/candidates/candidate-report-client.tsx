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
} from "@/types/api";

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
  const [screening, setScreening] = useState(false);

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
    const interval = window.setInterval(() => void loadPage(false), 3000);
    return () => window.clearInterval(interval);
  }, [candidate?.status, loadPage]);

  async function handleScreen() {
    if (!candidate) {
      return;
    }
    setScreening(true);
    setScreeningError(null);
    try {
      await screenCandidate(candidate.id);
      if (historicalRunId) {
        router.push(`/candidates/${candidate.id}`);
      } else {
        await loadPage(false);
      }
    } catch (screenError) {
      setScreeningError(
        getErrorMessage(
          screenError,
          "The AI analysis could not be completed. You can retry screening.",
        ),
      );
      await loadPage(false);
    } finally {
      setScreening(false);
    }
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

  return (
    <div className="page-stack report-page">
      {screening ? <AnalysisWorkflow candidateName={candidateName} /> : null}

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
        <Alert tone="warning" title="Latest screening attempt did not complete">
          <p>The most recent completed report is shown below. Review screening history for details.</p>
        </Alert>
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
              disabled={screening || candidate.status === "processing" || !resumeReady}
              onClick={() => void handleScreen()}
            >
              {screening
                ? "Analyzing…"
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
          <strong>{report?.screening_run.model_name ?? "Not recorded"}</strong>
        </div>
      </section>

      {error ? <Alert title="Report unavailable">{error}</Alert> : null}
      {screeningError ? (
        <Alert title="Screening failed">
          <p>{screeningError}</p>
          <button className="text-button" type="button" onClick={() => void handleScreen()}>
            Retry screening
          </button>
        </Alert>
      ) : null}

      {candidate.status === "processing" && !screening ? (
        <Alert tone="info" title="Candidate screening is in progress">
          This page will refresh when the current analysis finishes.
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
          title={candidate.status === "failed" ? "Screening failed" : "No completed screening yet"}
          description={
            candidate.status === "failed"
              ? "The AI analysis could not be completed. Review the safe error in history and retry when ready."
              : "Start screening to create an evidence-grounded report for recruiter review."
          }
          action={
            <button
              className="button button-primary"
              type="button"
              disabled={screening || candidate.status === "processing" || !resumeReady}
              onClick={() => void handleScreen()}
            >
              {candidate.status === "failed" ? "Retry screening" : "Screen candidate"}
            </button>
          }
        />
      ) : (
        <>
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
