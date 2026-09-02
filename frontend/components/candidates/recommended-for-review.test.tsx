import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RecommendedForReview } from "@/components/candidates/recommended-for-review";
import type { CandidateComparisonItem } from "@/types/api";

function prioritized(id: number, name: string, priority: number): CandidateComparisonItem {
  return {
    candidate_id: id,
    name,
    email: null,
    original_filename: `${name}.pdf`,
    status: "completed",
    created_at: "2026-09-02T00:00:00Z",
    resume_extraction_status: "completed",
    latest_completed_run_id: id + 20,
    latest_completed_at: "2026-09-02T00:01:00Z",
    active_screening_run_id: null,
    active_screening_stage: null,
    active_screening_stage_updated_at: null,
    required: { supported: 5 - priority, partial: 0, no_evidence: priority - 1, total: 4 },
    preferred: { supported: 4 - priority, partial: 0, no_evidence: priority - 1, total: 3 },
    needs_verification_count: priority - 1,
    review_priority: priority,
    review_label: priority === 1 ? "strong_evidence" : "moderate_evidence",
    comparable_evidence: id === 2,
  };
}

describe("RecommendedForReview", () => {
  it("shows only the first three transparent evidence summaries", () => {
    render(
      <RecommendedForReview
        candidates={[
          prioritized(1, "Candidate A", 1),
          prioritized(2, "Candidate B", 2),
          prioritized(3, "Candidate C", 3),
          prioritized(4, "Candidate D", 4),
          { ...prioritized(5, "Unscreened", 5), review_priority: null, review_label: null },
        ]}
      />,
    );

    expect(screen.getByRole("heading", { name: "Recommended for Review" })).toBeInTheDocument();
    expect(screen.getByText(/not an AI hiring score/i)).toBeInTheDocument();
    expect(screen.getByText("Candidate A")).toBeInTheDocument();
    expect(screen.getByText("Candidate B")).toBeInTheDocument();
    expect(screen.getByText("Candidate C")).toBeInTheDocument();
    expect(screen.queryByText("Candidate D")).not.toBeInTheDocument();
    expect(screen.queryByText("Unscreened")).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "View evidence" })).toHaveLength(3);
    expect(screen.getByText("Comparable evidence coverage")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/best candidate|recommended hire|%/i);
  });

  it("does not render when no candidate has a completed prioritized result", () => {
    const { container } = render(<RecommendedForReview candidates={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
