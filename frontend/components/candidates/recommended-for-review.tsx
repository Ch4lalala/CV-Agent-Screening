import Link from "next/link";

import { candidateDisplayName } from "@/lib/format";
import type { CandidateComparisonItem, ReviewLabel } from "@/types/api";

const labelCopy: Record<ReviewLabel, { title: string; description: string }> = {
  strong_evidence: {
    title: "Strong Evidence Coverage",
    description: "All required criteria are supported by resume evidence.",
  },
  moderate_evidence: {
    title: "Moderate Evidence Coverage",
    description: "Some required criteria have documented support or partial evidence.",
  },
  needs_verification: {
    title: "Needs Verification",
    description: "Required criteria still need recruiter review.",
  },
};

export function RecommendedForReview({
  candidates,
}: {
  candidates: CandidateComparisonItem[];
}) {
  const prioritized = candidates
    .filter(
      (candidate) =>
        candidate.review_priority !== null
        && candidate.review_label !== null
        && candidate.required !== null
        && candidate.preferred !== null,
    )
    .slice(0, 3);

  if (prioritized.length === 0) {
    return null;
  }

  return (
    <section className="panel recommended-review" aria-labelledby="recommended-review-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Vacancy evidence overview</p>
          <h2 id="recommended-review-title">Recommended for Review</h2>
          <p>
            Candidates are ordered by documented evidence coverage against
            recruiter-defined requirements, not an AI hiring score.
          </p>
        </div>
      </div>
      <div className="recommended-review-grid">
        {prioritized.map((candidate) => {
          const copy = labelCopy[candidate.review_label!];
          return (
            <article className="recommended-review-card" key={candidate.candidate_id}>
              <div className="recommended-review-rank" aria-label={`Review priority ${candidate.review_priority}`}>
                {candidate.review_priority}
              </div>
              <div className="recommended-review-heading">
                <h3>{candidateDisplayName(candidate.name, candidate.original_filename)}</h3>
                <span className={`review-label review-label-${candidate.review_label}`}>
                  {copy.title}
                </span>
              </div>
              <p>{copy.description}</p>
              {candidate.comparable_evidence ? (
                <p className="comparable-evidence-note">Comparable evidence coverage</p>
              ) : null}
              <dl className="recommended-review-metrics">
                <div>
                  <dt>Required criteria</dt>
                  <dd>{candidate.required!.supported}/{candidate.required!.total} supported</dd>
                </div>
                <div>
                  <dt>Preferred criteria</dt>
                  <dd>{candidate.preferred!.supported}/{candidate.preferred!.total} supported</dd>
                </div>
                <div>
                  <dt>Unresolved criteria</dt>
                  <dd>{candidate.needs_verification_count}</dd>
                </div>
              </dl>
              <Link className="text-button" href={`/candidates/${candidate.candidate_id}`}>
                View evidence
              </Link>
            </article>
          );
        })}
      </div>
      <p className="recommended-review-note">
        Priority controls review order only. Recruiters remain responsible for every decision.
      </p>
    </section>
  );
}
