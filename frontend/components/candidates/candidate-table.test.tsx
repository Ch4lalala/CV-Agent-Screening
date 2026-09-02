import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  CandidateTable,
  sortComparisonCandidates,
} from "@/components/candidates/candidate-table";
import type { CandidateComparisonItem } from "@/types/api";

function candidate(
  overrides: Partial<CandidateComparisonItem> = {},
): CandidateComparisonItem {
  return {
    candidate_id: 7,
    name: "Budi",
    email: "budi@example.com",
    original_filename: "budi.pdf",
    status: "completed",
    created_at: "2026-09-02T00:00:00Z",
    resume_extraction_status: "completed",
    latest_completed_run_id: 10,
    latest_completed_at: "2026-09-02T00:00:10Z",
    active_screening_run_id: null,
    active_screening_stage: null,
    active_screening_stage_updated_at: null,
    required: { supported: 4, partial: 0, no_evidence: 0, total: 4 },
    preferred: { supported: 2, partial: 0, no_evidence: 1, total: 3 },
    needs_verification_count: 1,
    review_priority: 1,
    review_label: "strong_evidence",
    comparable_evidence: false,
    ...overrides,
  };
}

describe("CandidateTable comparison and screening actions", () => {
  it("renders transparent counts and no unexplained score", () => {
    const unscreened = candidate({
      candidate_id: 8,
      name: "Unscreened",
      status: "uploaded",
      latest_completed_run_id: null,
      latest_completed_at: null,
      required: null,
      preferred: null,
      needs_verification_count: null,
      review_priority: null,
      review_label: null,
    });
    render(
      <CandidateTable
        rows={[candidate(), unscreened]}
        screeningCandidateId={null}
        screeningErrors={{}}
        onScreen={vi.fn()}
        onViewProgress={vi.fn()}
      />,
    );

    const screenedRow = screen.getByText("Budi").closest("tr");
    expect(screenedRow).not.toBeNull();
    expect(within(screenedRow!).getByText("4/4 supported")).toBeInTheDocument();
    expect(within(screenedRow!).getByText("2/3 supported")).toBeInTheDocument();
    expect(within(screenedRow!).getByText("Priority 1 · Strong Evidence")).toBeInTheDocument();
    const unscreenedRow = screen.getByText("Unscreened").closest("tr");
    expect(unscreenedRow).not.toBeNull();
    expect(within(unscreenedRow!).getAllByText("—")).toHaveLength(3);
    expect(document.body.textContent).not.toMatch(/fit score|hire score|%/i);
  });

  it("replaces Screen with View progress for an authoritative processing row", async () => {
    const row = candidate({
      status: "processing",
      review_priority: null,
      review_label: null,
      active_screening_run_id: 11,
      active_screening_stage: "match_evidence",
      active_screening_stage_updated_at: "2026-09-02T00:00:02Z",
    });
    const viewProgress = vi.fn();
    const user = userEvent.setup();
    render(
      <CandidateTable
        rows={[row]}
        screeningCandidateId={null}
        screeningErrors={{}}
        onScreen={vi.fn()}
        onViewProgress={viewProgress}
      />,
    );

    expect(screen.queryByRole("button", { name: "Screen" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "View progress" }));
    expect(viewProgress).toHaveBeenCalledWith(row);
  });

  it("offers Retry after a failed run", async () => {
    const row = candidate({
      status: "failed",
      review_priority: null,
      review_label: null,
    });
    const startScreening = vi.fn();
    const user = userEvent.setup();
    render(
      <CandidateTable
        rows={[row]}
        screeningCandidateId={null}
        screeningErrors={{}}
        onScreen={startScreening}
        onViewProgress={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(startScreening).toHaveBeenCalledWith(row);
  });

  it("supports recommended, newest, and stable name sorting", async () => {
    const recommended = candidate({ name: "Zulu", candidate_id: 1, review_priority: 1 });
    const newest = candidate({
      name: "Alpha",
      candidate_id: 2,
      created_at: "2026-09-03T00:00:00Z",
      review_priority: 2,
    });
    expect(sortComparisonCandidates([newest, recommended], "recommended")[0]).toBe(recommended);
    expect(sortComparisonCandidates([newest, recommended], "newest")[0]).toBe(newest);
    expect(sortComparisonCandidates([recommended, newest], "name")[0]).toBe(newest);

    const user = userEvent.setup();
    render(
      <CandidateTable
        rows={[recommended, newest]}
        screeningCandidateId={null}
        screeningErrors={{}}
        onScreen={vi.fn()}
        onViewProgress={vi.fn()}
      />,
    );
    await user.selectOptions(screen.getByLabelText("Sort candidates"), "name");
    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]).getByText("Alpha")).toBeInTheDocument();
  });
});
