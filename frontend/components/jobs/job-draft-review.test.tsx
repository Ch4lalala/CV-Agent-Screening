import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { JobDraftReview } from "@/components/jobs/job-draft-review";
import {
  createJob,
  createRequirement,
  deleteJob,
} from "@/lib/api/client";
import type { JobImportDraft } from "@/types/api";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api/client", () => ({
  createJob: vi.fn(),
  createRequirement: vi.fn(),
  deleteJob: vi.fn(),
  getErrorMessage: (_error: unknown, fallback: string) => fallback,
}));

const initialDraft: JobImportDraft = {
  title: "Backend Engineer Intern",
  description: "Minimum Qualifications: Git. Preferred Qualifications: Docker.",
  requirements: [
    {
      name: "Git",
      description: "Version control experience.",
      type: "required",
    },
    {
      name: "Docker",
      description: "Container experience.",
      type: "preferred",
    },
  ],
  warnings: [],
};

describe("JobDraftReview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(createJob).mockResolvedValue({
      id: 42,
      user_id: 1,
      title: initialDraft.title ?? "",
      description: initialDraft.description,
      status: "draft",
      created_at: "2026-09-01T00:00:00Z",
      updated_at: "2026-09-01T00:00:00Z",
    });
    vi.mocked(createRequirement).mockImplementation(async (jobId, input) => ({
      id: Math.random(),
      job_id: jobId,
      name: input.name,
      description: input.description ?? null,
      requirement_type: input.requirement_type,
      priority: input.priority ?? null,
      created_at: "2026-09-01T00:00:00Z",
    }));
    vi.mocked(deleteJob).mockResolvedValue(undefined);
  });

  it("pre-populates generated requirements and supports edit, delete, type change, and add", async () => {
    const user = userEvent.setup();
    render(
      <JobDraftReview
        initialDraft={initialDraft}
        onRevise={vi.fn()}
        reviseLabel="Back"
      />,
    );

    expect(screen.getByDisplayValue("Git")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Docker")).toBeInTheDocument();

    const firstName = screen.getAllByLabelText("Name")[0];
    await user.clear(firstName);
    await user.type(firstName, "Git workflows");
    expect(screen.getByDisplayValue("Git workflows")).toBeInTheDocument();

    const typeSelectors = screen.getAllByLabelText("Type");
    await user.selectOptions(typeSelectors[1], "required");
    expect(typeSelectors[1]).toHaveValue("required");

    await user.click(screen.getAllByRole("button", { name: "Remove" })[0]);
    expect(screen.queryByDisplayValue("Git workflows")).not.toBeInTheDocument();

    const preferredGroup = screen
      .getByRole("heading", { name: "Preferred qualifications" })
      .closest(".draft-requirement-group");
    expect(preferredGroup).not.toBeNull();
    await user.click(within(preferredGroup as HTMLElement).getByRole("button", { name: /Add requirement/ }));
    expect(screen.getAllByLabelText("Name")).toHaveLength(2);
  });

  it("persists only the recruiter-confirmed requirements as separate rows", async () => {
    const user = userEvent.setup();
    render(
      <JobDraftReview
        initialDraft={initialDraft}
        onRevise={vi.fn()}
        reviseLabel="Back"
      />,
    );

    await user.clear(screen.getByDisplayValue("Git"));
    await user.type(screen.getAllByLabelText("Name")[0], "Git collaboration");
    await user.selectOptions(screen.getAllByLabelText("Type")[1], "required");
    await user.click(screen.getByRole("button", { name: "Confirm & create vacancy" }));

    expect(createJob).toHaveBeenCalledOnce();
    expect(createRequirement).toHaveBeenCalledTimes(2);
    expect(createRequirement).toHaveBeenNthCalledWith(1, 42, {
      name: "Git collaboration",
      description: "Version control experience.",
      requirement_type: "required",
      priority: 1,
    });
    expect(createRequirement).toHaveBeenNthCalledWith(2, 42, {
      name: "Docker",
      description: "Container experience.",
      requirement_type: "required",
      priority: 2,
    });
    expect(push).toHaveBeenCalledWith("/jobs/42");
  });

  it("shows the graceful manual-entry fallback message", () => {
    render(
      <JobDraftReview
        initialDraft={{ ...initialDraft, requirements: [] }}
        onRevise={vi.fn()}
        reviseLabel="Back"
        fallbackMessage="Qualification suggestions could not be generated. You can add them manually."
      />,
    );

    expect(screen.getByText(/Qualification suggestions could not be generated/)).toBeInTheDocument();
    expect(screen.getByText("No required qualifications in this draft.")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Add requirement/ })).toHaveLength(2);
  });
});
