import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { candidateDisplayName, formatDate } from "@/lib/format";
import type { Candidate, ResumeMetadata, ScreeningRun } from "@/types/api";

export interface CandidateRow {
  candidate: Candidate;
  resume: ResumeMetadata | null;
  activeRun: ScreeningRun | null;
}

export function CandidateTable({
  rows,
  screeningCandidateId,
  screeningErrors,
  onScreen,
  onViewProgress,
}: {
  rows: CandidateRow[];
  screeningCandidateId: number | null;
  screeningErrors: Record<number, string>;
  onScreen: (candidate: Candidate) => void;
  onViewProgress: (candidate: Candidate, run: ScreeningRun | null) => void;
}) {
  if (rows.length === 0) {
    return (
      <EmptyState
        icon="CV"
        title="No candidates yet"
        description="Upload a PDF resume above to begin evidence-grounded screening."
      />
    );
  }

  return (
    <div className="candidate-table-wrap">
      <table className="candidate-table">
        <thead>
          <tr>
            <th>Candidate</th>
            <th>Resume</th>
            <th>Screening state</th>
            <th>Added</th>
            <th><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ candidate, resume, activeRun }) => {
            const isScreening = screeningCandidateId === candidate.id;
            const resumeReady = resume?.extraction_status === "completed";
            return (
              <tr key={candidate.id}>
                <td>
                  <div className="candidate-cell">
                    <span className="candidate-avatar" aria-hidden="true">
                      {candidateDisplayName(candidate.name, candidate.original_filename)
                        .slice(0, 1)
                        .toUpperCase()}
                    </span>
                    <span>
                      <strong>{candidateDisplayName(candidate.name, candidate.original_filename)}</strong>
                      <small>{candidate.email ?? "No email provided"}</small>
                    </span>
                  </div>
                  {screeningErrors[candidate.id] ? (
                    <p className="row-error">{screeningErrors[candidate.id]}</p>
                  ) : null}
                </td>
                <td>
                  <div className="resume-cell">
                    <strong>{candidate.original_filename ?? "No PDF attached"}</strong>
                    <small>
                      {resume
                        ? resume.extraction_status === "completed"
                          ? `${resume.page_count} page${resume.page_count === 1 ? "" : "s"} · Ready`
                          : resume.message ?? `Extraction ${resume.extraction_status}`
                        : "Resume metadata unavailable"}
                    </small>
                  </div>
                </td>
                <td>
                  <StatusBadge
                    status={isScreening ? "processing" : candidate.status}
                    label={isScreening ? "Analyzing" : undefined}
                  />
                </td>
                <td>{formatDate(candidate.created_at)}</td>
                <td>
                  <div className="table-actions">
                    <Link className="button button-small button-secondary" href={`/candidates/${candidate.id}`}>
                      {candidate.status === "completed" ? "View report" : "View"}
                    </Link>
                    {candidate.status === "processing" ? (
                      <button
                        className="button button-small button-primary"
                        type="button"
                        onClick={() => onViewProgress(candidate, activeRun)}
                      >
                        View progress
                      </button>
                    ) : candidate.status !== "completed" ? (
                      <button
                        className="button button-small button-primary"
                        type="button"
                        disabled={
                          isScreening || !resumeReady
                        }
                        title={!resumeReady ? "A successfully extracted resume is required" : undefined}
                        onClick={() => onScreen(candidate)}
                      >
                        {candidate.status === "failed" ? "Retry" : "Screen"}
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
