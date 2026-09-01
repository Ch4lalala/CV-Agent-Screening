"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CandidateTable, type CandidateRow } from "@/components/candidates/candidate-table";
import { CandidateUpload } from "@/components/candidates/candidate-upload";
import { PageHeader } from "@/components/layout/page-header";
import { AnalysisWorkflow } from "@/components/screening/analysis-workflow";
import { Alert } from "@/components/ui/alert";
import { LoadingState } from "@/components/ui/loading-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { RequirementManager } from "@/components/jobs/requirement-manager";
import {
  getCandidateResume,
  getCandidates,
  getErrorMessage,
  getJob,
  getRequirements,
  screenCandidate,
  updateJob,
} from "@/lib/api/client";
import { candidateDisplayName, formatDate } from "@/lib/format";
import type { Candidate, Job, JobRequirement, JobStatus } from "@/types/api";

export function JobDetailClient({ jobId }: { jobId: number }) {
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [requirements, setRequirements] = useState<JobRequirement[]>([]);
  const [candidateRows, setCandidateRows] = useState<CandidateRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusSaving, setStatusSaving] = useState(false);
  const [screeningCandidate, setScreeningCandidate] = useState<Candidate | null>(null);
  const [screeningErrors, setScreeningErrors] = useState<Record<number, string>>({});

  const loadRequirements = useCallback(async () => {
    setRequirements(await getRequirements(jobId));
  }, [jobId]);

  const loadCandidates = useCallback(async () => {
    const candidates = await getCandidates(jobId);
    const rows = await Promise.all(
      candidates.map(async (candidate): Promise<CandidateRow> => {
        try {
          return { candidate, resume: await getCandidateResume(candidate.id) };
        } catch {
          return { candidate, resume: null };
        }
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
    setScreeningCandidate(candidate);
    setScreeningErrors((current) => ({ ...current, [candidate.id]: "" }));
    try {
      await screenCandidate(candidate.id);
      router.push(`/candidates/${candidate.id}`);
    } catch (screenError) {
      setScreeningErrors((current) => ({
        ...current,
        [candidate.id]: getErrorMessage(
          screenError,
          "The AI analysis could not be completed. Try screening again.",
        ),
      }));
      try {
        await loadCandidates();
      } catch {
        setError("Screening failed, and the candidate list could not be refreshed. Reload the page to see the latest state.");
      }
    } finally {
      setScreeningCandidate(null);
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

  return (
    <div className="page-stack">
      {screeningCandidate ? (
        <AnalysisWorkflow
          candidateName={candidateDisplayName(
            screeningCandidate.name,
            screeningCandidate.original_filename,
          )}
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
            <p>Screen one candidate at a time and review evidence before any human decision.</p>
          </div>
          <span className="section-count">{candidateRows.length} candidates</span>
        </div>
        <CandidateTable
          rows={candidateRows}
          screeningCandidateId={screeningCandidate?.id ?? null}
          screeningErrors={screeningErrors}
          onScreen={(candidate) => void handleScreen(candidate)}
        />
      </section>
    </div>
  );
}
