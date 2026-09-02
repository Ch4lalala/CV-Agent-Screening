import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CandidateTable, type CandidateRow } from "@/components/candidates/candidate-table";

const baseCandidate = {
  id: 7,
  job_id: 3,
  name: "Budi",
  email: "budi@example.com",
  original_filename: "budi.pdf",
  created_at: "2026-09-02T00:00:00Z",
  updated_at: "2026-09-02T00:00:00Z",
} as const;

const resume = {
  original_filename: "budi.pdf",
  page_count: 1,
  extraction_status: "completed" as const,
  text_length: 120,
  message: null,
};

describe("CandidateTable screening actions", () => {
  it("replaces Screen with View progress for an authoritative processing row", async () => {
    const run = {
      id: 11,
      candidate_id: 7,
      status: "processing" as const,
      current_stage: "match_evidence" as const,
      current_stage_updated_at: "2026-09-02T00:00:02Z",
      model_name: "test-model",
      started_at: "2026-09-02T00:00:00Z",
      finished_at: null,
      error_message: null,
      created_at: "2026-09-02T00:00:00Z",
    };
    const rows: CandidateRow[] = [
      { candidate: { ...baseCandidate, status: "processing" }, resume, activeRun: run },
    ];
    const viewProgress = vi.fn();
    const user = userEvent.setup();
    render(
      <CandidateTable
        rows={rows}
        screeningCandidateId={null}
        screeningErrors={{}}
        onScreen={vi.fn()}
        onViewProgress={viewProgress}
      />,
    );

    expect(screen.queryByRole("button", { name: "Screen" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "View progress" }));
    expect(viewProgress).toHaveBeenCalledWith(rows[0].candidate, run);
  });

  it("offers Retry after a failed run", async () => {
    const candidate = { ...baseCandidate, status: "failed" as const };
    const screenCandidate = vi.fn();
    const user = userEvent.setup();
    render(
      <CandidateTable
        rows={[{ candidate, resume, activeRun: null }]}
        screeningCandidateId={null}
        screeningErrors={{}}
        onScreen={screenCandidate}
        onViewProgress={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(screenCandidate).toHaveBeenCalledWith(candidate);
  });
});
