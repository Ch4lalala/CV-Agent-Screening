"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { candidateDisplayName } from "@/lib/format";
import type { CandidateComparisonItem, CoverageCounts } from "@/types/api";

type CandidateSort = "recommended" | "newest" | "name";

const reviewLabels = {
  strong_evidence: "Strong Evidence",
  moderate_evidence: "Moderate Evidence",
  needs_verification: "Needs Verification",
} as const;

function coverageText(coverage: CoverageCounts | null): string {
  return coverage ? `${coverage.supported}/${coverage.total} supported` : "—";
}

function coverageDetails(coverage: CoverageCounts | null): string | undefined {
  return coverage
    ? `${coverage.partial} partial · ${coverage.no_evidence} no evidence`
    : undefined;
}

function statusOrder(candidate: CandidateComparisonItem): number {
  if (candidate.review_priority !== null) return 0;
  if (candidate.status === "processing") return 1;
  if (candidate.status === "uploaded") return 2;
  return 3;
}

export function sortComparisonCandidates(
  rows: CandidateComparisonItem[],
  sort: CandidateSort,
): CandidateComparisonItem[] {
  return [...rows].sort((left, right) => {
    if (sort === "name") {
      return candidateDisplayName(left.name, left.original_filename).localeCompare(
        candidateDisplayName(right.name, right.original_filename),
      ) || left.candidate_id - right.candidate_id;
    }
    if (sort === "newest") {
      return Date.parse(right.created_at) - Date.parse(left.created_at)
        || right.candidate_id - left.candidate_id;
    }
    return (
      statusOrder(left) - statusOrder(right)
      || (left.review_priority ?? Number.MAX_SAFE_INTEGER)
        - (right.review_priority ?? Number.MAX_SAFE_INTEGER)
      || Date.parse(right.created_at) - Date.parse(left.created_at)
      || left.candidate_id - right.candidate_id
    );
  });
}

export function CandidateTable({
  rows,
  screeningCandidateId,
  screeningErrors,
  onScreen,
  onViewProgress,
}: {
  rows: CandidateComparisonItem[];
  screeningCandidateId: number | null;
  screeningErrors: Record<number, string>;
  onScreen: (candidate: CandidateComparisonItem) => void;
  onViewProgress: (candidate: CandidateComparisonItem) => void;
}) {
  const [sort, setSort] = useState<CandidateSort>("recommended");
  const sortedRows = useMemo(() => sortComparisonCandidates(rows, sort), [rows, sort]);

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
    <>
      <div className="candidate-sort-control">
        <label htmlFor="candidate-sort">Sort candidates</label>
        <select
          id="candidate-sort"
          value={sort}
          onChange={(event) => setSort(event.target.value as CandidateSort)}
        >
          <option value="recommended">Recommended first</option>
          <option value="newest">Newest</option>
          <option value="name">Name</option>
        </select>
      </div>
      <div className="candidate-table-wrap">
        <table className="candidate-table">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Required</th>
              <th>Preferred</th>
              <th>Needs Review</th>
              <th>Screening State</th>
              <th><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((candidate) => {
              const isScreening = screeningCandidateId === candidate.candidate_id;
              const resumeReady = candidate.resume_extraction_status === "completed";
              const displayName = candidateDisplayName(
                candidate.name,
                candidate.original_filename,
              );
              return (
                <tr key={candidate.candidate_id}>
                  <td>
                    <div className="candidate-cell">
                      <span className="candidate-avatar" aria-hidden="true">
                        {displayName.slice(0, 1).toUpperCase()}
                      </span>
                      <span>
                        <strong>{displayName}</strong>
                        <small>{candidate.email ?? "No email provided"}</small>
                        {candidate.review_priority !== null && candidate.review_label ? (
                          <small className="candidate-priority-copy">
                            Priority {candidate.review_priority} · {reviewLabels[candidate.review_label]}
                          </small>
                        ) : null}
                        {candidate.comparable_evidence ? (
                          <small>Comparable evidence coverage</small>
                        ) : null}
                      </span>
                    </div>
                    {screeningErrors[candidate.candidate_id] ? (
                      <p className="row-error">{screeningErrors[candidate.candidate_id]}</p>
                    ) : null}
                  </td>
                  <td>
                    <strong>{coverageText(candidate.required)}</strong>
                    {candidate.required ? <small>{coverageDetails(candidate.required)}</small> : null}
                  </td>
                  <td>
                    <strong>{coverageText(candidate.preferred)}</strong>
                    {candidate.preferred ? <small>{coverageDetails(candidate.preferred)}</small> : null}
                  </td>
                  <td>
                    <strong>
                      {candidate.needs_verification_count === null
                        ? "—"
                        : candidate.needs_verification_count}
                    </strong>
                  </td>
                  <td>
                    <StatusBadge
                      status={isScreening ? "processing" : candidate.status}
                      label={isScreening ? "Analyzing" : undefined}
                    />
                  </td>
                  <td>
                    <div className="table-actions">
                      {candidate.latest_completed_run_id !== null ? (
                        <Link
                          className="button button-small button-secondary"
                          href={`/candidates/${candidate.candidate_id}`}
                        >
                          View evidence
                        </Link>
                      ) : (
                        <Link
                          className="button button-small button-secondary"
                          href={`/candidates/${candidate.candidate_id}`}
                        >
                          View
                        </Link>
                      )}
                      {candidate.status === "processing" ? (
                        <button
                          className="button button-small button-primary"
                          type="button"
                          onClick={() => onViewProgress(candidate)}
                        >
                          View progress
                        </button>
                      ) : candidate.status !== "completed" ? (
                        <button
                          className="button button-small button-primary"
                          type="button"
                          disabled={isScreening || !resumeReady}
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
    </>
  );
}
