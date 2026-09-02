import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AnalysisWorkflow } from "@/components/screening/analysis-workflow";

describe("AnalysisWorkflow", () => {
  it("shows persisted completed/current/waiting stages with one active spinner", async () => {
    const close = vi.fn();
    const user = userEvent.setup();
    const { container } = render(
      <AnalysisWorkflow
        candidateName="Budi CV"
        status="processing"
        currentStage="match_evidence"
        onClose={close}
      />,
    );

    expect(
      screen.getByText("Understanding job requirements").closest(".workflow-step"),
    ).toHaveClass("workflow-step-completed");
    expect(
      screen.getByText("Extracting candidate profile").closest(".workflow-step"),
    ).toHaveClass("workflow-step-completed");
    expect(
      screen.getByText("Matching resume evidence").closest(".workflow-step"),
    ).toHaveClass("workflow-step-current");
    expect(
      screen.getByText("Checking uncertainty").closest(".workflow-step"),
    ).toHaveClass("workflow-step-waiting");
    expect(container.querySelectorAll(".workflow-step-icon i")).toHaveLength(1);
    expect(screen.getByText(/continues even if you close/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Continue in background" }));
    expect(close).toHaveBeenCalledOnce();
  });

  it("offers explicit report and retry actions for terminal states", async () => {
    const viewReport = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <AnalysisWorkflow
        candidateName="Budi CV"
        status="completed"
        currentStage="completed"
        onClose={vi.fn()}
        onViewReport={viewReport}
      />,
    );

    expect(screen.getByRole("heading", { name: "Screening complete" })).toBeInTheDocument();
    expect(screen.getAllByText("Completed")).toHaveLength(6);
    await user.click(screen.getByRole("button", { name: "View candidate report" }));
    expect(viewReport).toHaveBeenCalledOnce();

    const retry = vi.fn();
    rerender(
      <AnalysisWorkflow
        candidateName="Budi CV"
        status="failed"
        currentStage="failed"
        onClose={vi.fn()}
        onRetry={retry}
      />,
    );
    expect(screen.getByRole("heading", { name: "Screening failed" })).toBeInTheDocument();
    expect(screen.queryByText(/provider returned/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry screening" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
