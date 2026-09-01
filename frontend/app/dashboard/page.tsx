"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Alert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { getCandidates, getErrorMessage, getJobs } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import type { Job } from "@/types/api";

interface DashboardJob extends Job {
  candidateCount: number | null;
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<DashboardJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const jobList = await getJobs();
      const withCounts = await Promise.all(
        jobList.map(async (job) => {
          try {
            const candidates = await getCandidates(job.id);
            return { ...job, candidateCount: candidates.length };
          } catch {
            return { ...job, candidateCount: null };
          }
        }),
      );
      setJobs(withCounts);
    } catch (loadError) {
      setError(getErrorMessage(loadError, "Unable to load vacancies."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Recruitment overview"
        title="Vacancies"
        description="Create roles, define the evidence that matters, and review every candidate with context."
        actions={
          <Link className="button button-primary" href="/jobs/new">
            <span aria-hidden="true">＋</span> Create vacancy
          </Link>
        }
      />

      <section className="metric-strip" aria-label="Vacancy summary">
        <div>
          <span className="metric-value">{jobs.length}</span>
          <span className="metric-label">Total vacancies</span>
        </div>
        <div>
          <span className="metric-value">
            {jobs.filter((job) => job.status === "active").length}
          </span>
          <span className="metric-label">Active roles</span>
        </div>
        <div>
          <span className="metric-value">
            {jobs.reduce((total, job) => total + (job.candidateCount ?? 0), 0)}
          </span>
          <span className="metric-label">Candidates</span>
        </div>
        <div className="metric-principle">
          <span className="metric-symbol" aria-hidden="true">
            ≠
          </span>
          <span>
            <strong>No black-box scores</strong>
            <small>Every finding links back to evidence.</small>
          </span>
        </div>
      </section>

      {error ? (
        <Alert title="Vacancies unavailable">
          <p>{error}</p>
          <button className="text-button" type="button" onClick={() => void loadJobs()}>
            Try again
          </button>
        </Alert>
      ) : null}

      {loading ? <LoadingState label="Loading vacancies" /> : null}

      {!loading && !error && jobs.length === 0 ? (
        <EmptyState
          icon="＋"
          title="No vacancies yet"
          description="Create your first vacancy, then define the required and preferred evidence for the role."
          action={
            <Link className="button button-primary" href="/jobs/new">
              Create your first vacancy
            </Link>
          }
        />
      ) : null}

      {!loading && jobs.length > 0 ? (
        <section aria-labelledby="vacancy-list-title">
          <div className="section-heading">
            <div>
              <p className="section-kicker">Your workspace</p>
              <h2 id="vacancy-list-title">Open recruitment work</h2>
            </div>
            <span className="section-count">{jobs.length} roles</span>
          </div>
          <div className="job-grid">
            {jobs.map((job) => (
              <article className="job-card" key={job.id}>
                <div className="job-card-top">
                  <span className="job-icon" aria-hidden="true">
                    {job.title.slice(0, 1).toUpperCase()}
                  </span>
                  <StatusBadge status={job.status} />
                </div>
                <div>
                  <p className="job-created">Created {formatDate(job.created_at)}</p>
                  <h3>{job.title}</h3>
                  <p className="job-description">{job.description}</p>
                </div>
                <div className="job-card-footer">
                  <span>
                    <strong>{job.candidateCount ?? "—"}</strong>
                    {job.candidateCount === 1 ? " candidate" : " candidates"}
                  </span>
                  <Link className="arrow-link" href={`/jobs/${job.id}`}>
                    View vacancy <span aria-hidden="true">→</span>
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
